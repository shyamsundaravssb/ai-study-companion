import uuid
import json
from typing import TypedDict, List
from langgraph.graph import StateGraph, END
from pydantic import ValidationError

from app.db.session import SessionLocal
from app.models.concept import Concept
from app.ai.retrieval import retrieve, RetrievedChunk
from app.observability.ai_logger import logged_generate
from app.ai.providers.groq_provider import GroqProvider
from app.schemas.assessment import GradingOutput

groq_provider_instance = GroqProvider()
MODEL_NAME = "openai/gpt-oss-20b"
MAX_RETRIES = 2

class GradingState(TypedDict):
    project_id: uuid.UUID
    question_text: str
    user_answer: str
    concept_id: uuid.UUID | None
    concept_name: str | None
    context_chunks: List[RetrievedChunk]
    raw_response: str
    parsed_grading: dict
    validation_error: str
    retry_count: int

def fetch_concept_name(state: GradingState) -> dict:
    if not state.get("concept_id"):
        return {"concept_name": None}
        
    db = SessionLocal()
    try:
        concept = db.query(Concept).filter(Concept.id == state["concept_id"]).first()
        return {"concept_name": concept.name if concept else None}
    finally:
        db.close()

async def retrieve_context(state: GradingState) -> dict:
    query = state["question_text"]
    if state.get("concept_name"):
        query += f" {state['concept_name']}"
        
    chunks = await retrieve(project_id=state["project_id"], query=query)
    return {"context_chunks": chunks}

async def generate_grading(state: GradingState) -> dict:
    chunks = state.get("context_chunks", [])
    
    context_text = "\n\n".join(
        [f"--- CHUNK {i+1} ---\n{c.text}" for i, c in enumerate(chunks[:10])]
    )
    
    system_prompt = (
        "You are an expert AI Grader. Grade the user's answer to the given open-ended question based ONLY on the provided context material.\n\n"
        "Output your response strictly as a JSON object matching this schema:\n"
        '{\n'
        '  "understanding_score": float (0.0 to 1.0, representing how well the user understood the core concept),\n'
        '  "accuracy_score": float (0.0 to 1.0, representing factual accuracy of the answer),\n'
        '  "missing_concepts": ["concept 1", "concept 2"] (list of strings representing what was missed, empty if none),\n'
        '  "feedback_text": "Constructive feedback for the user"\n'
        '}\n'
    )
    
    user_prompt = f"Context Material:\n{context_text}\n\nQuestion:\n{state['question_text']}\n\nUser's Answer:\n{state['user_answer']}"
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]
    
    if state.get("validation_error"):
        messages.append({"role": "assistant", "content": state["raw_response"]})
        messages.append({"role": "user", "content": f"Your previous response failed validation with the following error: {state['validation_error']}. Please fix the JSON output."})
        
    response = await logged_generate(
        provider=groq_provider_instance,
        feature="assessment_grading",
        project_id=state["project_id"],
        messages=messages,
        model=MODEL_NAME,
        temperature=0.1,
        response_format={"type": "json_object"}
    )
    
    return {"raw_response": response.text}

def validate_grading(state: GradingState) -> dict:
    raw_response = state["raw_response"]
    retry_count = state.get("retry_count", 0)
    
    try:
        data = json.loads(raw_response)
        validated = GradingOutput.model_validate(data)
        return {"parsed_grading": validated.model_dump(), "validation_error": None, "retry_count": retry_count + 1}
    except json.JSONDecodeError as e:
        return {"validation_error": f"JSON Decode Error: {str(e)}", "retry_count": retry_count + 1}
    except ValidationError as e:
        return {"validation_error": f"Pydantic Validation Error: {str(e)}", "retry_count": retry_count + 1}

def route_validation(state: GradingState) -> str:
    if state.get("validation_error") is None:
        return END
    
    if state.get("retry_count", 0) >= MAX_RETRIES:
        raise RuntimeError("Failed to generate valid grading output from AI after retries.")
        
    return "generate_grading"

workflow = StateGraph(GradingState)

workflow.add_node("fetch_concept_name", fetch_concept_name)
workflow.add_node("retrieve_context", retrieve_context)
workflow.add_node("generate_grading", generate_grading)
workflow.add_node("validate_grading", validate_grading)

workflow.set_entry_point("fetch_concept_name")
workflow.add_edge("fetch_concept_name", "retrieve_context")
workflow.add_edge("retrieve_context", "generate_grading")
workflow.add_edge("generate_grading", "validate_grading")

workflow.add_conditional_edges(
    "validate_grading",
    route_validation,
    {
        END: END,
        "generate_grading": "generate_grading"
    }
)

grading_app = workflow.compile()
