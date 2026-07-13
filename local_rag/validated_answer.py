from pydantic import BaseModel, Field, field_validator, ValidationInfo
from typing import List


class ValidatedRAGAnswer(BaseModel):
    found: bool = Field(description="Whether the answer was found in the excerpts")
    answer: str = Field(description="The answer, or a brief explanation if not found")
    sources: List[int] = Field(description="Excerpt numbers supporting the answer")

    @field_validator("sources")
    @classmethod
    def sources_must_exist(cls, v: List[int], info: ValidationInfo) -> List[int]:
        n_excerpts = (info.context or {}).get("n_excerpts")

        if n_excerpts is None:
            return v   # no context provided — skip the check

        invalid = [s for s in v if s < 1 or s > n_excerpts]

        if invalid:
            raise ValueError(
                f"Hallucinated source(s): {invalid}. "
                f"Only excerpts 1-{n_excerpts} were provided to the model."
            )

        return v
    
    from pydantic import model_validator

    @model_validator(mode="after")
    def found_requires_sources(self):
        if self.found and not self.sources:
            raise ValueError(
                "Answer claims found=True but cites no sources. "
                "A grounded answer must reference at least one excerpt."
            )
        return self