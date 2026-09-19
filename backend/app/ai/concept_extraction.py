import uuid
import json
import logging
from typing import List, Dict

from pydantic import ValidationError

from app.observability.ai_logger import logged_generate
from app.ai.providers.groq_provider import GroqProvider
from app.schemas.concept import ConceptExtractionResponse

logger = logging.getLogger(__name__)

groq_provider_instance = GroqProvider()
MODEL_NAME = "openai/gpt-oss-20b"
MAX_RETRIES = 1

async def extract_concepts(project_id: uuid.UUID, chunks_text: str) -> ConceptExtractionResponse:
    system_prompt = (
        "You are an expert educational AI. Your task is to identify the core learning concepts covered in the provided material.\n"
        "Return a structured list of these core concepts. Each concept must have a short 'name' (e.g. 'Supervised Learning', 'Backpropagation') "
        "and a one-sentence 'description'.\n"
        "Aim for a reasonable count (e.g. 5-15 concepts). Do not return one mega-concept, and do not return dozens of trivial ones. Focus on the main ideas.\n\n"
        "Output your response strictly as a JSON object matching this schema:\n"
        '{\n'
        '  "concepts": [\n'
        '    {\n'
        '      "name": "Concept Name",\n'
        '      "description": "One sentence description."\n'
        '    }\n'
        '  ]\n'
        '}'
    )
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Material Context:\n{chunks_text}"}
    ]
    
    retry_count = 0
    validation_error = None
    raw_response = ""
    
    while retry_count <= MAX_RETRIES:
        if validation_error:
            messages.append({"role": "assistant", "content": raw_response})
            messages.append({"role": "user", "content": f"Your previous response failed validation with the following error: {validation_error}. Please fix the JSON output."})
            
        try:
            response = await logged_generate(
                provider=groq_provider_instance,
                feature="concept_extraction",
                project_id=project_id,
                messages=messages,
                model=MODEL_NAME,
                temperature=0.3,
                response_format={"type": "json_object"}
            )
            raw_response = response.text
            
            data = json.loads(raw_response)
            validated = ConceptExtractionResponse.model_validate(data)
            return validated
            
        except (json.JSONDecodeError, ValidationError) as e:
            validation_error = str(e)
            retry_count += 1
            logger.warning(f"Concept extraction validation failed (retry {retry_count}): {validation_error}")
            
    raise ValueError(f"Failed to generate valid concept extraction output after {MAX_RETRIES} retries. Last error: {validation_error}")
