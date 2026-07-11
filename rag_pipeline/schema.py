from pydantic import BaseModel, Field
from typing import List


class RAGAnswer(BaseModel):
    found: bool = Field(description="Whether the answer was found in the provided excerpts")
    answer: str = Field(description="The answer to the question, or a brief explanation if not found")
    sources: List[int] = Field(description="List of excerpt numbers used to support the answer, e.g. [1, 2]")