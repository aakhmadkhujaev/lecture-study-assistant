"""Validated structured models for generated study guides."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


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


DiagramType = Literal[
    "flow",
    "concept_map",
    "hierarchy",
    "process",
    "comparison",
    "complexity",
    "data_structure",
]


class VisualNode(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    label: str


class VisualRelationship(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source: str
    target: str
    label: str | None = None


class VisualModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str
    purpose: str
    diagram_type: DiagramType
    nodes: list[VisualNode]
    relationships: list[VisualRelationship]
    explanation: str
    source_references: list[SourceReference]

    @model_validator(mode="after")
    def relationships_reference_nodes(self) -> "VisualModel":
        node_ids = {node.id for node in self.nodes}
        invalid = [
            relationship
            for relationship in self.relationships
            if relationship.source not in node_ids or relationship.target not in node_ids
        ]
        if invalid:
            raise ValueError("Visual relationships must reference existing node ids.")
        return self


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
    visual_models: list[VisualModel] = Field(default_factory=list)
    sources: list[SourceReference]
