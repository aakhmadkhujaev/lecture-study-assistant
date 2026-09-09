"""Focused tests for presentation-only study-guide PDF generation."""

import json
from pathlib import Path

import pymupdf

from app.ai.schemas import StudyGuide
from app.pdf.renderer import PDFService


def _reference(index: int = 1) -> dict[str, object]:
    return {
        "filename": "lecture.pdf",
        "source_type": "page",
        "source_index": index,
    }


def _guide(populated: bool = True, long_content: bool = False) -> StudyGuide:
    reference = _reference()
    if not populated:
        return StudyGuide(
            lecture_title="Lecture 1",
            overview="",
            learning_objectives=[],
            key_concepts=[],
            definitions=[],
            formulas=[],
            exam_topics=[],
            common_confusions=[],
            practice_questions=[],
            quick_revision=[],
            knowledge_gaps=[],
            sources=[],
        )
    overview = "A concise overview with Unicode O(n²) → ≥ ≤."
    if long_content:
        overview += " " + ("This is extended source-supported study material. " * 900)
    return StudyGuide(
        lecture_title="Lecture 1",
        overview=overview,
        learning_objectives=["Explain the algorithm."],
        key_concepts=[
            {
                "concept": "Foundational concept",
                "simple_explanation": "This is required to understand later material.",
                "important_points": ["It is explicitly covered."],
                "example": "A lecture example.",
                "remember": "Keep this in mind.",
                "importance": "must_know",
                "source_references": [reference],
            },
            {
                "concept": "Supporting concept",
                "simple_explanation": "This supports the main material.",
                "important_points": [],
                "example": None,
                "remember": None,
                "importance": "supporting",
                "source_references": [reference],
            },
            {
                "concept": "Important concept",
                "simple_explanation": "This is useful supporting material.",
                "important_points": [],
                "example": None,
                "remember": None,
                "importance": "important",
                "source_references": [reference],
            },
        ],
        definitions=[
            {
                "term": "Algorithm",
                "simple_definition": "A precise sequence of steps.",
                "source_references": [reference],
            }
        ],
        formulas=[
            {
                "formula": "O(n²)",
                "meaning": "The lecture's stated complexity expression.",
                "source_references": [reference],
            }
        ],
        exam_topics=[
            {
                "topic": "Complexity comparison",
                "why_important": "Supports revision of the main material.",
                "source_references": [reference],
            }
        ],
        common_confusions=[
            {
                "topic": "Two search methods",
                "confusion": "They have the same process.",
                "clarification": "The lecture distinguishes their steps.",
                "source_references": [reference],
            }
        ],
        practice_questions=[
            {
                "question_type": "definition",
                "question": "What is an algorithm?",
                "model_answer": "A precise sequence of steps.",
                "source_references": [reference],
            }
        ],
        quick_revision=["Review the complexity expression O(n²) →."],
        knowledge_gaps=[
            {
                "topic": "Unexplained application",
                "reason": "The lecture mentions it without enough detail.",
                "what_is_missing": "Worked application steps.",
                "recommended_action": "Review the relevant source material.",
                "source_references": [reference],
            }
        ],
        sources=[reference],
    )


def _pdf_text(path: Path) -> str:
    with pymupdf.open(path) as document:
        return "\n".join(page.get_text() for page in document)


def test_minimal_guide_generates_valid_pdf_without_empty_headings(tmp_path: Path) -> None:
    output_path = tmp_path / "Study_Guide.pdf"

    PDFService().generate(_guide(populated=False), output_path)

    assert output_path.exists()
    assert output_path.read_bytes().startswith(b"%PDF")
    text = _pdf_text(output_path)
    assert "Lecture Study Guide" in text
    assert "Lecture Overview" not in text
    assert "Practice Questions" not in text
    assert "Sources" not in text


def test_populated_sections_priorities_questions_sources_and_unicode_render(tmp_path: Path) -> None:
    output_path = tmp_path / "Study_Guide.pdf"

    PDFService().generate(_guide(), output_path, course_name="Algorithms")

    text = _pdf_text(output_path)
    for value in (
        "Lecture Overview",
        "Learning Objectives",
        "Key Concepts",
        "Important Definitions",
        "Formulas & Algorithms",
        "Important for Revision",
        "Must Know",
        "Supporting",
        "Common Confusions",
        "Practice Questions",
        "Model answer",
        "Quick Revision",
        "Knowledge Gaps",
        "Sources",
        "lecture.pdf",
        "O(n²)",
    ):
        assert value in text


def test_long_content_flows_across_pages_and_pdf_does_not_call_gemini(
    tmp_path: Path, monkeypatch,
) -> None:
    def fail_if_called(*args: object, **kwargs: object) -> str:
        raise AssertionError("PDF generation must not invoke Gemini")

    monkeypatch.setattr("app.ai.gemini_provider.GeminiProvider.generate", fail_if_called)
    output_path = tmp_path / "Study_Guide.pdf"

    PDFService().generate(_guide(long_content=True), output_path)

    with pymupdf.open(output_path) as document:
        assert len(document) > 1


def test_existing_study_guide_json_can_be_loaded_and_rendered(tmp_path: Path) -> None:
    json_path = tmp_path / "Study_Guide.json"
    output_path = tmp_path / "Study_Guide.pdf"
    guide = _guide()
    json_path.write_text(json.dumps(guide.model_dump(mode="json"), ensure_ascii=False), encoding="utf-8")

    loaded_guide = StudyGuide.model_validate(json.loads(json_path.read_text(encoding="utf-8")))
    PDFService().generate(loaded_guide, output_path)

    assert "Lecture 1" in _pdf_text(output_path)