"""Tests for grounded structured study-guide generation."""

import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from pydantic import ValidationError
from google import genai
from google.genai import _common, models, types

from config.settings import Settings

from app.ai.generator import (
    EmptyLectureContentError,
    SourceTraceabilityError,
    StructuredResponseError,
    generate_study_guide,
)
from app.ai.gemini_provider import GeminiProvider
from app.ai.openai_provider import OpenAIProvider
from app.ai.prompts import SYSTEM_PROMPT, build_source_prompt
from app.ai.provider import AIConfigurationError, AIRequestError
from app.ai.schemas import SourceReference, StudyGuide
from app.ai.service import (
    StudyGuideAlreadyExistsError,
    generate_lecture_study_guide,
    save_study_guide,
)
from app.processors.models import Document, Section
from app.services.library_service import (
    create_course,
    create_lecture,
    initialize_library,
    upload_material,
)


class FakeProvider:
    def __init__(self, responses: list[str]) -> None:
        self.responses = responses
        self.prompts: list[tuple[str, str]] = []

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        self.prompts.append((system_prompt, user_prompt))
        return self.responses.pop(0)


def _document(filename: str = "lecture.pdf") -> Document:
    return Document(
        filename=filename,
        file_type=".pdf",
        sections=(Section(source_index=1, source_type="page", text="Gradient descent updates parameters."),),
    )


def _guide_payload(filename: str = "lecture.pdf", source_index: int = 1) -> dict:
    reference = {
        "filename": filename,
        "source_type": "page",
        "source_index": source_index,
    }
    return {
        "lecture_title": "Lecture 01",
        "overview": "The lecture introduces gradient descent.",
        "learning_objectives": ["Explain the update idea."],
        "key_concepts": [
            {
                "concept": "Gradient descent",
                "simple_explanation": "A parameter update method.",
                "important_points": ["It uses a gradient."],
                "example": None,
                "remember": "Follow the update direction.",
                "importance": "must_know",
                "source_references": [reference],
            }
        ],
        "definitions": [],
        "formulas": [],
        "exam_topics": [],
        "common_confusions": [],
        "practice_questions": [],
        "quick_revision": ["Gradient descent updates parameters."],
        "knowledge_gaps": [],
        "sources": [reference],
    }


def test_study_guide_prompt_requires_grounded_exam_oriented_extraction() -> None:
    prompt = build_source_prompt("Algorithms", [_document()])
    system_prompt = " ".join(SYSTEM_PROMPT.lower().split())

    assert "do not use outside knowledge" in system_prompt
    assert "leave it as an empty list" in system_prompt
    assert "binary search" in system_prompt
    assert "number of operations or running time scales" in system_prompt
    assert "must still describe scaling with input size" in system_prompt
    assert "must know" in system_prompt
    assert "usually 2-6" in system_prompt
    assert "only the deduplicated source locations actually used" in system_prompt
    assert "original material is the authority" in system_prompt
    assert "do not silently resolve" in system_prompt
    assert "generic input -> process -> output" in system_prompt
    assert "0-4 visuals" in system_prompt
    assert "difference in strategy, operations, or growth" in system_prompt
    assert "data structure -> operations -> efficiency" in system_prompt
    assert "linear search versus binary search" in system_prompt
    assert "list/dict/set/tuple trade-offs" in system_prompt
    assert "prefer them over a generic algorithm shape" in system_prompt
    assert "not a decorative illustration" in system_prompt
    assert "Apply all section rules" in prompt


def test_mocked_supported_lecture_content_remains_traceable() -> None:
    payload = _guide_payload()
    reference = payload["sources"][0]
    payload["definitions"] = [
        {
            "term": "Gradient descent",
            "simple_definition": "A parameter update method.",
            "source_references": [reference],
        }
    ]
    payload["formulas"] = [
        {
            "formula": "O(log n)",
            "meaning": "The lecture uses binary search on a sorted list as its example.",
            "source_references": [reference],
        }
    ]
    payload["practice_questions"] = [
        {
            "question_type": "formula_interpretation",
            "question": "What complexity example does the lecture give?",
            "model_answer": "Binary search on a sorted list is given as an O(log n) example.",
            "source_references": [reference],
        }
    ]
    provider = FakeProvider([json.dumps(payload)])

    guide = generate_study_guide(provider, "Lecture 01", [_document()])

    assert guide.definitions[0].term == "Gradient descent"
    assert guide.formulas[0].formula == "O(log n)"
    assert guide.practice_questions[0].question_type == "formula_interpretation"
    assert guide.formulas[0].source_references[0].source_index == 1
    assert guide.sources == [SourceReference.model_validate(reference)]


def test_visual_references_are_validated_and_added_to_used_sources() -> None:
    payload = _guide_payload()
    reference = payload["sources"][0]
    payload["visual_models"] = [
        {
            "title": "Gradient descent flow",
            "purpose": "Show the update sequence.",
            "diagram_type": "process",
            "nodes": [
                {"id": "gradient", "label": "Gradient"},
                {"id": "update", "label": "Update"},
            ],
            "relationships": [
                {"source": "gradient", "target": "update", "label": "drives"}
            ],
            "explanation": "The gradient drives the parameter update.",
            "source_references": [reference, reference],
        }
    ]
    provider = FakeProvider([json.dumps(payload)])

    guide = generate_study_guide(provider, "Lecture 01", [_document()])

    assert guide.visual_models[0].title == "Gradient descent flow"
    assert guide.sources == [SourceReference.model_validate(reference)]


def test_invalid_visual_reference_uses_existing_repair_flow() -> None:
    invalid = _guide_payload()
    invalid["visual_models"] = [
        {
            "title": "Unsupported flow",
            "purpose": "Show a flow.",
            "diagram_type": "flow",
            "nodes": [{"id": "a", "label": "A"}],
            "relationships": [],
            "explanation": "A simple flow.",
            "source_references": [
                {"filename": "missing.pdf", "source_type": "page", "source_index": 1}
            ],
        }
    ]
    valid = _guide_payload()
    provider = FakeProvider([json.dumps(invalid), json.dumps(valid)])

    generate_study_guide(provider, "Lecture 01", [_document()])

    assert len(provider.prompts) == 2
    assert "invalid source reference" in provider.prompts[1][1].lower()


def test_source_inventory_keeps_only_deduplicated_used_references() -> None:
    payload = _guide_payload()
    used_reference = payload["sources"][0]
    unused_reference = {
        "filename": "lecture.pdf",
        "source_type": "page",
        "source_index": 2,
    }
    payload["sources"] = [used_reference, unused_reference, used_reference]
    documents = [
        _document(),
        Document(
            filename="lecture.pdf",
            file_type=".pdf",
            sections=(Section(source_index=2, source_type="page", text="Context only."),),
        ),
    ]
    provider = FakeProvider([json.dumps(payload)])

    guide = generate_study_guide(provider, "Lecture 01", documents)

    assert [(source.filename, source.source_index) for source in guide.sources] == [
        ("lecture.pdf", 1)
    ]
    assert guide.key_concepts[0].source_references == [
        SourceReference.model_validate(used_reference)
    ]


def test_source_reference_validation() -> None:
    reference = SourceReference(filename="lecture.pdf", source_type="page", source_index=1)
    assert reference.source_index == 1
    with pytest.raises(ValidationError):
        SourceReference(filename="", source_type="page", source_index=1)
    with pytest.raises(ValidationError):
        SourceReference(filename="lecture.pdf", source_type="page", source_index=0)


def test_study_guide_rejects_extra_fields() -> None:
    payload = _guide_payload()
    payload["unexpected"] = True
    with pytest.raises(ValidationError):
        StudyGuide.model_validate(payload)


def test_generator_rejects_invalid_source_then_repairs() -> None:
    invalid = _guide_payload(source_index=99)
    valid = _guide_payload()
    provider = FakeProvider([json.dumps(invalid), json.dumps(valid)])

    guide = generate_study_guide(provider, "Lecture 01", [_document()])

    assert guide.sources[0].source_index == 1
    assert len(provider.prompts) == 2
    assert "invalid source reference" in provider.prompts[1][1].lower()


def test_generator_rejects_invalid_source_after_failed_repair() -> None:
    invalid = json.dumps(_guide_payload(source_index=99))
    provider = FakeProvider([invalid, invalid])

    with pytest.raises(SourceTraceabilityError):
        generate_study_guide(provider, "Lecture 01", [_document()])


def test_generator_repairs_malformed_json() -> None:
    provider = FakeProvider(["not json", json.dumps(_guide_payload())])

    guide = generate_study_guide(provider, "Lecture 01", [_document()])

    assert guide.lecture_overview == "The lecture introduces gradient descent."
    assert len(provider.prompts) == 2


def test_generator_reports_schema_failure_after_repair() -> None:
    malformed = json.dumps({"unexpected": True})
    provider = FakeProvider([malformed, malformed])

    with pytest.raises(StructuredResponseError):
        generate_study_guide(provider, "Lecture 01", [_document()])


def test_empty_extracted_content_is_rejected() -> None:
    empty = Document(filename="empty.pdf", file_type=".pdf", sections=())
    provider = FakeProvider([])

    with pytest.raises(EmptyLectureContentError):
        generate_study_guide(provider, "Lecture 01", [empty])


def test_missing_openai_configuration_is_clear() -> None:
    settings = Settings(
        storage_root=Path("data"),
        database_path=Path("data/test.db"),
        ai_api_key=None,
        openai_api_key=None,
        ai_model="",
    )
    with pytest.raises(Exception, match="OPENAI_API_KEY"):
        OpenAIProvider(settings)


def test_gemini_provider_generates_structured_json(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeModels:
        def __init__(self) -> None:
            self.request = None

        def generate_content(self, **kwargs: object) -> SimpleNamespace:
            self.request = kwargs
            return SimpleNamespace(text=json.dumps(_guide_payload()))

    fake_models = FakeModels()
    monkeypatch.setattr(
        "app.ai.gemini_provider.genai.Client",
        lambda api_key: SimpleNamespace(models=fake_models),
    )
    settings = Settings(
        storage_root=Path("data"),
        database_path=Path("data/test.db"),
        ai_api_key="gemini-key",
        gemini_api_key="gemini-key",
        ai_model="gemini-test-model",
    )

    guide = generate_study_guide(
        GeminiProvider(settings), "Lecture 01", [_document()]
    )

    assert guide.lecture_overview == "The lecture introduces gradient descent."
    assert fake_models.request is not None
    assert fake_models.request["model"] == "gemini-test-model"
    config = fake_models.request["config"]
    assert config.response_mime_type == "application/json"
    assert config.response_json_schema["type"] == "object"
    assert "additionalProperties" not in config.response_json_schema
    assert "additional_properties" not in config.response_json_schema


def test_gemini_serialized_schema_has_no_unsupported_additional_properties(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeModels:
        def generate_content(self, **kwargs: object) -> SimpleNamespace:
            self.request = kwargs
            return SimpleNamespace(text=json.dumps(_guide_payload()))

    sdk_client = genai.Client(api_key="test-key")
    fake_models = FakeModels()
    monkeypatch.setattr(
        "app.ai.gemini_provider.genai.Client",
        lambda api_key: SimpleNamespace(models=fake_models),
    )
    settings = Settings(
        storage_root=Path("data"),
        database_path=Path("data/test.db"),
        ai_api_key="gemini-key",
        gemini_api_key="gemini-key",
        ai_model="gemini-test-model",
    )

    GeminiProvider(settings).generate("system", "user")
    config = fake_models.request["config"]
    parameters = types._GenerateContentParameters(
        model="gemini-test-model",
        contents="user",
        config=config,
    )
    request = models._GenerateContentParameters_to_mldev(
        sdk_client._api_client,
        parameters,
        None,
        parameters,
    )
    request.pop("config", None)
    wire_request = _common.encode_unserializable_types(
        _common.convert_to_dict(request)
    )
    serialized_schema = json.dumps(wire_request["generationConfig"]["responseJsonSchema"])

    assert "additional_properties" not in serialized_schema
    assert "additionalProperties" not in serialized_schema
    assert "key_concepts" in serialized_schema
    assert "source_references" in serialized_schema
    assert '"items"' in serialized_schema


def test_missing_gemini_configuration_is_clear() -> None:
    settings = Settings(
        storage_root=Path("data"),
        database_path=Path("data/test.db"),
        ai_api_key=None,
        gemini_api_key=None,
        ai_model="gemini-test-model",
    )

    with pytest.raises(AIConfigurationError, match="GEMINI_API_KEY"):
        GeminiProvider(settings)


def test_gemini_provider_maps_api_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    def failing_client(api_key: str) -> SimpleNamespace:
        raise RuntimeError("quota exceeded")

    monkeypatch.setattr("app.ai.gemini_provider.genai.Client", failing_client)
    settings = Settings(
        storage_root=Path("data"),
        database_path=Path("data/test.db"),
        ai_api_key="gemini-key",
        gemini_api_key="gemini-key",
        ai_model="gemini-test-model",
    )

    with pytest.raises(AIRequestError, match="quota exceeded"):
        GeminiProvider(settings)


def test_gemini_provider_maps_request_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    class FailingModels:
        def generate_content(self, **kwargs: object) -> None:
            raise RuntimeError("network failure")

    monkeypatch.setattr(
        "app.ai.gemini_provider.genai.Client",
        lambda api_key: SimpleNamespace(models=FailingModels()),
    )
    settings = Settings(
        storage_root=Path("data"),
        database_path=Path("data/test.db"),
        ai_api_key="gemini-key",
        gemini_api_key="gemini-key",
        ai_model="gemini-test-model",
    )

    with pytest.raises(AIRequestError, match="network failure"):
        GeminiProvider(settings).generate("system", "user")


def test_gemini_model_configuration_loads_from_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from config.settings import get_settings

    monkeypatch.setenv("GEMINI_API_KEY", "configured-key")
    monkeypatch.setenv("GEMINI_MODEL", "configured-model")

    settings = get_settings()

    assert settings.gemini_api_key == "configured-key"
    assert settings.ai_model == "configured-model"


def test_multiple_materials_preserve_filename_traceability() -> None:
    first = _document("lecture-a.pdf")
    second = Document(
        filename="lecture-b.pptx",
        file_type=".pptx",
        sections=(Section(source_index=2, source_type="slide", text="Algorithm steps."),),
    )
    payload = _guide_payload("lecture-a.pdf")
    second_reference = {
        "filename": "lecture-b.pptx", "source_type": "slide", "source_index": 2
    }
    payload["sources"].append(second_reference)
    payload["key_concepts"][0]["source_references"].append(second_reference)
    provider = FakeProvider([json.dumps(payload)])

    guide = generate_study_guide(provider, "Lecture 01", [first, second])

    assert {(source.filename, source.source_type, source.source_index) for source in guide.sources} == {
        ("lecture-a.pdf", "page", 1),
        ("lecture-b.pptx", "slide", 2),
    }
    assert "filename=lecture-b.pptx" in provider.prompts[0][1]


def test_guided_material_is_labeled_and_keeps_its_source_identity() -> None:
    original = _document("lecture.pdf")
    guided_reference = {
        "filename": "textbook.pdf",
        "source_type": "guided",
        "source_index": 1,
    }
    guided = Document(
        filename="textbook.pdf",
        file_type=".pdf",
        sections=(Section(source_index=1, source_type="page", text="A clarifying example."),),
        material_type="guided",
    )
    payload = _guide_payload()
    payload["key_concepts"][0]["source_references"].append(guided_reference)
    payload["sources"].append(guided_reference)
    provider = FakeProvider([json.dumps(payload)])

    guide = generate_study_guide(provider, "Lecture 01", [original, guided])

    prompt = provider.prompts[0][1]
    assert "=== ORIGINAL MATERIAL ===" in prompt
    assert "=== GUIDED MATERIAL ===" in prompt
    assert "filename=textbook.pdf" in prompt
    assert "material_type=guided" in prompt
    assert guided_reference in [source.model_dump() for source in guide.sources]


def test_guided_only_document_is_not_labeled_as_original() -> None:
    guided = Document(
        filename="textbook.pdf",
        file_type=".pdf",
        sections=(Section(source_index=1, source_type="page", text="Supporting text."),),
        material_type="guided",
    )
    guided_reference = {
        "filename": "textbook.pdf",
        "source_type": "guided",
        "source_index": 1,
    }
    payload = _guide_payload("textbook.pdf")
    payload["sources"] = [guided_reference]
    payload["key_concepts"][0]["source_references"] = [guided_reference]
    provider = FakeProvider([json.dumps(payload)])

    generate_study_guide(provider, "Lecture 01", [guided])

    prompt = provider.prompts[0][1]
    assert "material_type=guided" in prompt
    assert "=== GUIDED MATERIAL ===" in prompt
    assert "=== ORIGINAL MATERIAL ===" in prompt
    assert "filename=textbook.pdf\nmaterial_type=original" not in prompt


def test_original_only_prompt_has_no_guided_material_block() -> None:
    provider = FakeProvider([json.dumps(_guide_payload())])

    generate_study_guide(provider, "Lecture 01", [_document()])

    assert "=== GUIDED MATERIAL ===" not in provider.prompts[0][1]


def test_chunking_preserves_source_markers() -> None:
    documents = [
        Document(
            filename="lecture.pdf",
            file_type=".pdf",
            sections=(
                Section(source_index=1, source_type="page", text="First section."),
                Section(source_index=2, source_type="page", text="Second section."),
            ),
        )
    ]
    payload = _guide_payload()
    provider = FakeProvider([json.dumps(payload), json.dumps(payload), json.dumps(payload)])

    generate_study_guide(provider, "Lecture 01", documents, chunk_threshold=1)

    assert len(provider.prompts) == 3
    assert "source_index=1" in provider.prompts[0][1]
    assert "source_index=2" in provider.prompts[1][1]


def test_service_generates_and_saves_guide_for_multiple_materials(tmp_path: Path) -> None:
    settings = Settings(
        storage_root=tmp_path / "data",
        database_path=tmp_path / "data" / "library.db",
        ai_api_key=None,
        ai_model="",
    )
    initialize_library(settings)
    course = create_course(settings, "Algorithms")
    lecture = create_lecture(settings, course.id, "Lecture 01")
    first_material = upload_material(settings, lecture.id, "first.pdf", _pdf_bytes("First"))
    upload_material(settings, lecture.id, "second.pdf", _pdf_bytes("Second"))
    payload = _guide_payload(first_material.original_filename)
    provider = FakeProvider([json.dumps(payload)])

    guide, path = generate_lecture_study_guide(settings, lecture.id, provider=provider)

    assert path.name == "Study_Guide.json"
    saved = json.loads(path.read_text(encoding="utf-8"))
    assert "lecture_title" not in saved
    assert saved["lecture_overview"] == "The lecture introduces gradient descent."
    assert "filename=second.pdf" in provider.prompts[0][1]
    with pytest.raises(StudyGuideAlreadyExistsError):
        save_study_guide(settings, lecture.id, guide)


def test_service_assembles_current_original_and_guided_materials(tmp_path: Path) -> None:
    settings = Settings(
        storage_root=tmp_path / "data",
        database_path=tmp_path / "data" / "library.db",
        ai_api_key=None,
        ai_model="",
    )
    initialize_library(settings)
    course = create_course(settings, "Algorithms")
    lecture = create_lecture(settings, course.id, "Lecture 01")
    upload_material(settings, lecture.id, "lecture.pdf", _pdf_bytes("Original concept"))
    upload_material(
        settings,
        lecture.id,
        "textbook.pdf",
        _pdf_bytes("Guided explanation"),
        material_type="guided",
    )
    payload = _guide_payload()
    provider = FakeProvider([json.dumps(payload)])

    generate_lecture_study_guide(settings, lecture.id, provider=provider)

    prompt = provider.prompts[0][1]
    assert "filename=lecture.pdf" in prompt
    assert "filename=textbook.pdf" in prompt
    assert "material_type=original" in prompt
    assert "material_type=guided" in prompt


def test_duplicate_material_filenames_get_distinct_source_names(tmp_path: Path) -> None:
    settings = Settings(
        storage_root=tmp_path / "data",
        database_path=tmp_path / "data" / "library.db",
        ai_api_key=None,
        ai_model="",
    )
    initialize_library(settings)
    course = create_course(settings, "Databases")
    lecture = create_lecture(settings, course.id, "Lecture 02")
    upload_material(settings, lecture.id, "slides.pdf", _pdf_bytes("First copy"))
    upload_material(settings, lecture.id, "slides.pdf", _pdf_bytes("Second copy"))
    payload = _guide_payload("slides.pdf")
    payload["sources"].append(
        {"filename": "slides (1).pdf", "source_type": "page", "source_index": 1}
    )
    provider = FakeProvider([json.dumps(payload)])

    generate_lecture_study_guide(settings, lecture.id, provider=provider)

    assert "filename=slides.pdf" in provider.prompts[0][1]
    assert "filename=slides (1).pdf" in provider.prompts[0][1]


def _pdf_bytes(text: str) -> bytes:
    import pymupdf

    document = pymupdf.open()
    page = document.new_page()
    page.insert_text((72, 72), text)
    content = document.tobytes()
    document.close()
    return content
