import uuid
import json
import random
from typing import TypedDict, List
from langgraph.graph import StateGraph, END
from pydantic import ValidationError

from app.models.mastery import Mastery
from app.models.concept import Concept
from app.db.session import SessionLocal
from app.ai.retrieval import retrieve, RetrievedChunk
from app.observability.ai_logger import logged_generate
from app.ai.providers.groq_provider import GroqProvider
from app.schemas.quiz import QuizGenerationResponse

groq_provider_instance = GroqProvider()
MODEL_NAME = "openai/gpt-oss-20b"
MAX_RETRIES = 2

class QuizState(TypedDict):
    project_id: uuid.UUID
    concepts: List[dict]
    selected_concepts: List[dict]
    context_chunks: List[RetrievedChunk]
    raw_response: str
    parsed_quiz: dict
    validation_error: str
    retry_count: int

def fetch_concepts(state: QuizState) -> dict:
    db = SessionLocal()
    try:
        concepts = db.query(Concept).filter(Concept.project_id == state["project_id"]).all()
        masteries = db.query(Mastery).filter(Mastery.project_id == state["project_id"]).all()
        
        mastery_map = {m.concept_id: m.score for m in masteries}
        
        concept_list = []
        for c in concepts:
            concept_list.append({
                "id": c.id,
                "name": c.name,
                "description": c.description,
                "mastery_score": mastery_map.get(c.id, None)
            })
        return {"concepts": concept_list}
    finally:
        db.close()

def select_concepts(state: QuizState) -> dict:
    concepts = state["concepts"]
    if not concepts:
        return {"selected_concepts": []}
    
    # Weighting logic
    # Score < 0.4 -> weight 3 (highest priority for failing concepts)
    # No score -> weight 2 (broad coverage for untested)
    # Score < 0.8 -> weight 1
    # Score >= 0.8 -> weight 0.1
    
    weights = []
    for c in concepts:
        score = c["mastery_score"]
        if score is None:
            weights.append(2.0)
        elif score < 0.4:
            weights.append(3.0)
        elif score < 0.8:
            weights.append(1.0)
        else:
            weights.append(0.1)
            
    # Sample up to 5 concepts based on weights
    k = min(5, len(concepts))
    scored_concepts = []
    for c, w in zip(concepts, weights):
        scored_concepts.append((c, random.random() * w))
        
    scored_concepts.sort(key=lambda x: x[1], reverse=True)
    selected = [x[0] for x in scored_concepts[:k]]
    
    return {"selected_concepts": selected}

async def retrieve_context(state: QuizState) -> dict:
    selected = state["selected_concepts"]
    if not selected:
        return {"context_chunks": []}
        
    all_chunks = []
    for c in selected:
        chunks = await retrieve(project_id=state["project_id"], query=c["name"])
        all_chunks.extend(chunks)
        
    unique_texts = set()
    deduped_chunks = []
    for chunk in all_chunks:
        if chunk.text not in unique_texts:
            unique_texts.add(chunk.text)
            deduped_chunks.append(chunk)
            
    return {"context_chunks": deduped_chunks}

async def generate_quiz(state: QuizState) -> dict:
    selected = state["selected_concepts"]
    chunks = state["context_chunks"]
    
    if not selected:
        raise ValueError("No concepts available to test.")
        
    context_text = "\n\n".join(
        [f"--- CHUNK {i+1} ---\n{c.text}" for i, c in enumerate(chunks[:10])]
    )
    
    concept_instructions = []
    for c in selected:
        score = c["mastery_score"]
        if score is None:
            diff = "mix of foundational MCQ and simple open-ended"
        elif score < 0.4:
            diff = "foundational, mostly MCQ to build confidence"
        elif score < 0.8:
            diff = "intermediate, mixed MCQ and open-ended"
        else:
            diff = "advanced, mostly open-ended complex questions"
            
        concept_instructions.append(f"- Concept '{c['name']}' (ID: {str(c['id'])}): {diff}")
        
    concept_instructions_text = "\n".join(concept_instructions)
    
    system_prompt = (
        "You are an expert AI Tutor. Create a quiz for the user based on the provided context material. If the context is empty or insufficient, use your general knowledge to generate questions for the concepts.\n"
        "Generate a list of questions testing the following concepts, adhering to the requested difficulty:\n"
        f"{concept_instructions_text}\n\n"
        "CRITICAL REQUIREMENT: The final quiz MUST contain a mix of BOTH 'mcq' and 'open_ended' question types. Do not generate a quiz with only one type of question.\n\n"
        "Output your response strictly as a JSON object matching this schema:\n"
        '{\n'
        '  "questions": [\n'
        '    {\n'
        '      "type": "mcq" | "open_ended",\n'
        '      "concept_id": "UUID string of the tested concept",\n'
        '      "prompt_text": "The question text",\n'
        '      "options": [ {"text": "option 1"}, {"text": "option 2"} ] (only for mcq),\n'
        '      "correct_option_index": integer (0-indexed, only for mcq)\n'
        '    }\n'
        '  ]\n'
        '}\n'
        "Ensure all concept_ids match the provided IDs."
    )
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Context Material:\n{context_text}"}
    ]
    
    if state.get("validation_error"):
        messages.append({"role": "assistant", "content": state["raw_response"]})
        messages.append({"role": "user", "content": f"Your previous response failed validation with the following error: {state['validation_error']}. Please fix the JSON output."})
        
    response = await logged_generate(
        provider=groq_provider_instance,
        feature="quiz_generation",
        project_id=state["project_id"],
        messages=messages,
        model=MODEL_NAME,
        temperature=0.3,
        response_format={"type": "json_object"}
    )
    
    return {"raw_response": response.text}

def validate_quiz(state: QuizState) -> dict:
    raw_response = state["raw_response"]
    retry_count = state.get("retry_count", 0)
    
    try:
        data = json.loads(raw_response)
        validated = QuizGenerationResponse.model_validate(data)
        return {"parsed_quiz": validated.model_dump(), "validation_error": None, "retry_count": retry_count + 1}
    except json.JSONDecodeError as e:
        return {"validation_error": f"JSON Decode Error: {str(e)}", "retry_count": retry_count + 1}
    except ValidationError as e:
        return {"validation_error": f"Pydantic Validation Error: {str(e)}", "retry_count": retry_count + 1}

def route_validation(state: QuizState) -> str:
    if state.get("validation_error") is None:
        return END
    
    if state.get("retry_count", 0) >= MAX_RETRIES:
        raise RuntimeError("Failed to generate valid assessment output from AI after retries.")
        
    return "generate_quiz"


workflow = StateGraph(QuizState)

workflow.add_node("fetch_concepts", fetch_concepts)
workflow.add_node("select_concepts", select_concepts)
workflow.add_node("retrieve_context", retrieve_context)
workflow.add_node("generate_quiz", generate_quiz)
workflow.add_node("validate_quiz", validate_quiz)

workflow.set_entry_point("fetch_concepts")
workflow.add_edge("fetch_concepts", "select_concepts")
workflow.add_edge("select_concepts", "retrieve_context")
workflow.add_edge("retrieve_context", "generate_quiz")
workflow.add_edge("generate_quiz", "validate_quiz")

workflow.add_conditional_edges(
    "validate_quiz",
    route_validation,
    {
        END: END,
        "generate_quiz": "generate_quiz"
    }
)

quiz_app = workflow.compile()
