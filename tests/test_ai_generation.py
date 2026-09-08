"""Tests for grounded structured study-guide generation."""

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from config.settings import Settings

from app.ai.generator import (
    EmptyLectureContentError,
    SourceTraceabilityError,
    StructuredResponseError,
    generate_study_guide,
)
from app.ai.openai_provider import OpenAIProvider
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

    assert guide.lecture_title == "Lecture 01"
    assert len(provider.prompts) == 2


def test_generator_reports_schema_failure_after_repair() -> None:
    malformed = json.dumps({"lecture_title": "Lecture 01"})
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


def test_multiple_materials_preserve_filename_traceability() -> None:
    first = _document("lecture-a.pdf")
    second = Document(
        filename="lecture-b.pptx",
        file_type=".pptx",
        sections=(Section(source_index=2, source_type="slide", text="Algorithm steps."),),
    )
    payload = _guide_payload("lecture-a.pdf")
    payload["sources"].append(
        {"filename": "lecture-b.pptx", "source_type": "slide", "source_index": 2}
    )
    provider = FakeProvider([json.dumps(payload)])

    guide = generate_study_guide(provider, "Lecture 01", [first, second])

    assert {(source.filename, source.source_type, source.source_index) for source in guide.sources} == {
        ("lecture-a.pdf", "page", 1),
        ("lecture-b.pptx", "slide", 2),
    }
    assert "filename=lecture-b.pptx" in provider.prompts[0][1]


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
    assert json.loads(path.read_text(encoding="utf-8"))["lecture_title"] == "Lecture 01"
    assert guide.lecture_title == "Lecture 01"
    assert "filename=second.pdf" in provider.prompts[0][1]
    with pytest.raises(StudyGuideAlreadyExistsError):
        save_study_guide(settings, lecture.id, guide)


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
