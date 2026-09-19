from pydantic import BaseModel
from typing import List

class ExtractedConcept(BaseModel):
    name: str
    description: str

class ConceptExtractionResponse(BaseModel):
    concepts: List[ExtractedConcept]
