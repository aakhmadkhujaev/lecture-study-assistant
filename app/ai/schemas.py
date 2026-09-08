"""Validated structured models for generated study guides."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class SourceReference(BaseModel):
    """A traceable reference to extracted source material."""

    model_config = ConfigDict(extra="forbid")

    filename: str
    source_type: str
    source_index: int = Field(ge=1)

    @field_validator("filename", "source_type")
    @classmethod
    def must_not_be_empty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Source reference values cannot be empty.")
        return value.strip()


class KeyConcept(BaseModel):
    model_config = ConfigDict(extra="forbid")

    concept: str
    simple_explanation: str
    important_points: list[str]
    example: str | None = None
    remember: str | None = None
    importance: Literal["must_know", "important", "supporting"]
    source_references: list[SourceReference]


class Definition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    term: str
    simple_definition: str
    source_references: list[SourceReference]


class Formula(BaseModel):
    model_config = ConfigDict(extra="forbid")

    formula: str
    meaning: str
    source_references: list[SourceReference]


class ExamTopic(BaseModel):
    model_config = ConfigDict(extra="forbid")

    topic: str
    why_important: str
    source_references: list[SourceReference]


class CommonConfusion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    topic: str
    confusion: str
    clarification: str
    source_references: list[SourceReference]


class PracticeQuestion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question_type: Literal[
        "definition",
        "explanation",
        "comparison",
        "application",
        "why",
        "step_by_step",
        "formula_interpretation",
    ]
    question: str
    model_answer: str
    source_references: list[SourceReference]


class KnowledgeGap(BaseModel):
    model_config = ConfigDict(extra="forbid")

    topic: str
    reason: str
    what_is_missing: str
    recommended_action: str
    source_references: list[SourceReference]


class StudyGuide(BaseModel):
    """Canonical structured study guide artifact."""

    model_config = ConfigDict(extra="forbid")

    lecture_title: str
    overview: str
    learning_objectives: list[str]
    key_concepts: list[KeyConcept]
    definitions: list[Definition]
    formulas: list[Formula]
    exam_topics: list[ExamTopic]
    common_confusions: list[CommonConfusion]
    practice_questions: list[PracticeQuestion]
    quick_revision: list[str]
    knowledge_gaps: list[KnowledgeGap]
    sources: list[SourceReference]
