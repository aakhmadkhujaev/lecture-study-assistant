"""Focused tests for the locked StudyGuide Schema V2 contract."""

import json

import pytest
from pydantic import ValidationError

from app.ai.generator import generate_study_guide
from app.ai.schemas import (
    EngineeringConnection,
    KeyConcept,
    MentalModel,
    RealWorldApplication,
    SourceReference,
    StudyGuide,
    VisualModel,
)
from app.processors.models import Document, Section


REFERENCE = {
    "filename": "lecture.pdf",
    "source_type": "page",
    "source_index": 1,
}


def _application(number: int) -> dict[str, object]:
    return {
        "title": f"Application {number}",
        "problem": "The system needs efficient lookup.",
        "solution": "Use the covered data structure.",
        "why_this_concept": "It supports the required operation.",
        "impact": "Lookup performance improves.",
        "source_references": [REFERENCE],
    }


def _guide_payload() -> dict[str, object]:
    return {
        "lecture_overview": "A grounded overview.",
        "learning_objectives": ["Explain the concept."],
        "mental_model": {
            "core_idea": "A useful abstraction.",
            "components": ["Input", "Operation"],
            "relationships": ["Input is transformed by the operation."],
            "how_it_works": "The operation transforms the input.",
            "key_takeaway": "Choose it for the supported operation.",
        },
        "visual_models": [],
        "key_concepts": [
            {
                "name": "Hash table",
                "importance": "must_know",
                "definition": "A keyed lookup structure.",
                "explanation": "It maps keys to values.",
                "example": "A Python dict.",
                "use_when": "Fast average lookup is needed.",
                "avoid_when": "Memory use is tightly constrained.",
                "source_references": [REFERENCE],
            }
        ],
        "definitions": [],
        "formulas": [],
        "real_world_applications": [_application(1)],
        "engineering_connections": [
            {
                "concept": "Hash table",
                "real_world_problem": "Need fast lookup.",
                "engineering_decision": "Choose a hash table.",
                "implementation": "Use a Python dict.",
                "trade_offs": "Fast average lookup uses more memory.",
                "source_references": [REFERENCE],
            }
        ],
        "exam_topics": [],
        "common_confusions": [],
        "practice_questions": [],
        "knowledge_gaps": [],
        "quick_revision": [],
        "sources": [],
    }


def test_new_structured_models_validate() -> None:
    assert MentalModel.model_validate(_guide_payload()["mental_model"])
    assert KeyConcept.model_validate(_guide_payload()["key_concepts"][0])
    assert RealWorldApplication.model_validate(_application(1))
    assert EngineeringConnection.model_validate(_guide_payload()["engineering_connections"][0])


def test_real_world_applications_limit_is_three() -> None:
    payload = _guide_payload()
    payload["real_world_applications"] = [_application(number) for number in range(1, 4)]
    assert len(StudyGuide.model_validate(payload).real_world_applications) == 3

    payload["real_world_applications"] = [_application(number) for number in range(1, 5)]
    with pytest.raises(ValidationError):
        StudyGuide.model_validate(payload)


def test_unknown_fields_and_invalid_diagram_type_are_rejected() -> None:
    with pytest.raises(ValidationError):
        MentalModel.model_validate({"unexpected": True})
    with pytest.raises(ValidationError):
        VisualModel.model_validate(
            {
                "title": "Invalid",
                "purpose": "Test",
                "diagram_type": "decorative",
                "nodes": [],
                "relationships": [],
                "explanation": "Test",
                "source_references": [],
            }
        )


def test_invalid_visual_relationship_is_rejected() -> None:
    with pytest.raises(ValidationError):
        VisualModel.model_validate(
            {
                "title": "Invalid relationship",
                "purpose": "Test",
                "diagram_type": "flow",
                "nodes": [{"id": "known", "label": "Known"}],
                "relationships": [{"source": "missing", "target": "known"}],
                "explanation": "Test",
                "source_references": [],
            }
        )


def test_legacy_study_guide_without_v2_fields_still_loads() -> None:
    legacy = {
        "lecture_title": "Lecture 01",
        "overview": "Legacy overview.",
        "learning_objectives": [],
        "key_concepts": [
            {
                "concept": "Legacy concept",
                "simple_explanation": "Legacy explanation.",
                "important_points": ["Legacy point."],
                "example": None,
                "remember": None,
                "importance": "supporting",
                "source_references": [],
            }
        ],
        "definitions": [],
        "formulas": [],
        "exam_topics": [],
        "common_confusions": [],
        "practice_questions": [],
        "quick_revision": [],
        "knowledge_gaps": [],
        "sources": [],
    }
    guide = StudyGuide.model_validate(legacy)
    assert guide.lecture_overview == "Legacy overview."
    assert guide.visual_models == []
    assert guide.mental_model.core_idea == ""
    assert guide.key_concepts[0].name == "Legacy concept"


def test_schema_contains_all_and_only_locked_top_level_fields() -> None:
    expected = {
        "lecture_overview",
        "learning_objectives",
        "mental_model",
        "visual_models",
        "key_concepts",
        "definitions",
        "formulas",
        "real_world_applications",
        "engineering_connections",
        "exam_topics",
        "common_confusions",
        "practice_questions",
        "knowledge_gaps",
        "quick_revision",
        "sources",
    }
    assert set(StudyGuide.model_json_schema()["properties"]) == expected


def test_new_source_bearing_models_use_existing_validation_and_inventory() -> None:
    class FakeProvider:
        def __init__(self, responses: list[str]) -> None:
            self.responses = responses
            self.prompts: list[str] = []

        def generate(self, system_prompt: str, user_prompt: str) -> str:
            self.prompts.append(user_prompt)
            return self.responses.pop(0)

    invalid = _guide_payload()
    invalid["real_world_applications"] = [_application(1)]
    invalid["real_world_applications"][0]["source_references"] = [
        {**REFERENCE, "source_index": 9}
    ]
    provider = FakeProvider([json.dumps(invalid), json.dumps(_guide_payload())])
    guide = generate_study_guide(
        provider,
        "Lecture 01",
        [
            Document(
                filename="lecture.pdf",
                file_type=".pdf",
                sections=(Section(source_index=1, source_type="page", text="Content"),),
            )
        ],
    )

    assert len(provider.prompts) == 2
    assert "invalid source reference" in provider.prompts[1].lower()
    assert guide.sources == [SourceReference.model_validate(REFERENCE)]
