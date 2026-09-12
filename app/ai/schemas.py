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

    name: str
    definition: str
    explanation: str
    example: str | None = None
    importance: Literal["must_know", "important", "supporting"]
    use_when: str
    avoid_when: str
    source_references: list[SourceReference]

    @model_validator(mode="before")
    @classmethod
    def migrate_legacy_shape(cls, value: object) -> object:
        if not isinstance(value, dict) or "name" in value:
            return value
        legacy = dict(value)
        legacy["name"] = legacy.pop("concept")
        legacy["definition"] = legacy.pop("simple_explanation")
        points = legacy.pop("important_points", [])
        legacy["explanation"] = " ".join(points)
        legacy["use_when"] = ""
        legacy["avoid_when"] = legacy.pop("remember", "") or ""
        return legacy


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


class MentalModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    core_idea: str = ""
    components: list[str] = Field(default_factory=list)
    relationships: list[str] = Field(default_factory=list)
    how_it_works: str = ""
    key_takeaway: str = ""


class RealWorldApplication(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str
    problem: str
    solution: str
    why_this_concept: str
    impact: str
    source_references: list[SourceReference]


class EngineeringConnection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    concept: str
    real_world_problem: str
    engineering_decision: str
    implementation: str
    trade_offs: str
    source_references: list[SourceReference]


class StudyGuide(BaseModel):
    """Canonical structured study guide artifact."""

    model_config = ConfigDict(extra="forbid")

    lecture_overview: str = ""
    learning_objectives: list[str] = Field(default_factory=list)
    mental_model: MentalModel = Field(default_factory=MentalModel)
    visual_models: list[VisualModel] = Field(default_factory=list)
    key_concepts: list[KeyConcept] = Field(default_factory=list)
    definitions: list[Definition] = Field(default_factory=list)
    formulas: list[Formula] = Field(default_factory=list)
    real_world_applications: list[RealWorldApplication] = Field(
        default_factory=list, max_length=3
    )
    engineering_connections: list[EngineeringConnection] = Field(default_factory=list)
    exam_topics: list[ExamTopic] = Field(default_factory=list)
    common_confusions: list[CommonConfusion] = Field(default_factory=list)
    practice_questions: list[PracticeQuestion] = Field(default_factory=list)
    knowledge_gaps: list[KnowledgeGap] = Field(default_factory=list)
    quick_revision: list[str] = Field(default_factory=list)
    sources: list[SourceReference] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def migrate_legacy_shape(cls, value: object) -> object:
        if not isinstance(value, dict):
            return value
        migrated = dict(value)
        if "overview" in migrated:
            migrated.setdefault("lecture_overview", migrated.pop("overview"))
            migrated.pop("lecture_title", None)
        return migrated
