from pydantic import BaseModel, field_validator
from typing import Literal


class ConceptExtraction(BaseModel):
    concepts: list[str]
    equations: list[str]


class ClassifiedMatch(BaseModel):
    source: str          # textbook filename/ID
    chapter: str         # chapter number/title
    subchapter: str = "" # subchapter if applicable
    classification: Literal["EXPLAINS", "USES"]
    confidence: float    # 0.0 to 1.0
    reason: str


class Problem(BaseModel):
    question: str
    solution: str
    warning_disclaimer: str = "AI-generated solutions may contain errors. Verify independently."

    @field_validator("warning_disclaimer")
    @classmethod
    def disclaimer_must_be_present(cls, v: str) -> str:
        if not v:
            return "AI-generated solutions may contain errors. Verify independently."
        return v


class PracticeProblems(BaseModel):
    topic: str
    problems: list[Problem]
