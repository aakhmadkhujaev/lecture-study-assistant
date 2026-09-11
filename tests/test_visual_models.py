"""Focused tests for visual mental model schemas and rendering."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from app.ai.schemas import StudyGuide, VisualModel
from app.pdf.renderer import PDFService
from app.visuals.renderer import render_visual_flowables, render_visual_text


def _visual(diagram_type: str = "flow", long_label: bool = False) -> dict:
    label = "A very long educational label " * 20 if long_label else "Input"
    return {
        "title": "Algorithm flow",
        "purpose": "Show the main sequence.",
        "diagram_type": diagram_type,
        "nodes": [
            {"id": "input", "label": label},
            {"id": "output", "label": "Output"},
        ],
        "relationships": [
            {"source": "input", "target": "output", "label": "produces"}
        ],
        "explanation": "The process transforms input into output.",
        "source_references": [
            {"filename": "lecture.pdf", "source_type": "page", "source_index": 1}
        ],
    }


def test_visual_model_validates_and_rejects_invalid_types_and_relationships() -> None:
    visual = VisualModel.model_validate(_visual())
    assert visual.diagram_type == "flow"
    with pytest.raises(ValidationError):
        VisualModel.model_validate({**_visual(), "diagram_type": "decorative"})
    with pytest.raises(ValidationError):
        VisualModel.model_validate({**_visual(), "relationships": [
            {"source": "missing", "target": "output"}
        ]})


def test_visual_model_rejects_extra_fields_and_empty_nodes_are_renderable() -> None:
    with pytest.raises(ValidationError):
        VisualModel.model_validate({**_visual(), "unexpected": True})
    empty = VisualModel.model_validate({**_visual(), "nodes": [], "relationships": []})
    assert render_visual_text(empty) == "(No nodes)"


def test_existing_study_guide_without_visual_models_remains_backward_compatible() -> None:
    payload = {
        "lecture_title": "Lecture 01",
        "overview": "",
        "learning_objectives": [],
        "key_concepts": [],
        "definitions": [],
        "formulas": [],
        "exam_topics": [],
        "common_confusions": [],
        "practice_questions": [],
        "quick_revision": [],
        "knowledge_gaps": [],
        "sources": [],
    }
    guide = StudyGuide.model_validate(payload)
    assert guide.visual_models == []


@pytest.mark.parametrize(
    "diagram_type",
    ["flow", "concept_map", "hierarchy", "process", "comparison", "complexity", "data_structure"],
)
def test_all_supported_visual_types_render(diagram_type: str) -> None:
    visual = VisualModel.model_validate(_visual(diagram_type))
    assert render_visual_text(visual)
    assert render_visual_flowables(visual)


def test_long_unicode_labels_render_in_a_multi_page_pdf(tmp_path: Path) -> None:
    visual = VisualModel.model_validate(
        {
            **_visual("data_structure", long_label=True),
            "title": "Stack — модель",
            "explanation": "Unicode explanation: вершина → выход.",
        }
    )
    payload = {
        "lecture_title": "Lecture 01",
        "overview": "",
        "learning_objectives": [],
        "key_concepts": [],
        "definitions": [],
        "formulas": [],
        "exam_topics": [],
        "common_confusions": [],
        "practice_questions": [],
        "quick_revision": [],
        "knowledge_gaps": [],
        "visual_models": [visual.model_dump(mode="json")],
        "sources": [],
    }
    guide = StudyGuide.model_validate(payload)
    output = tmp_path / "Study_Guide.pdf"
    PDFService().generate(guide, output)
    assert output.exists()
    assert "Visual Mental Models" in _pdf_text(output)


def test_empty_visual_models_omit_pdf_section(tmp_path: Path) -> None:
    guide = StudyGuide.model_validate(
        {
            "lecture_title": "Lecture 01",
            "overview": "",
            "learning_objectives": [],
            "key_concepts": [],
            "definitions": [],
            "formulas": [],
            "exam_topics": [],
            "common_confusions": [],
            "practice_questions": [],
            "quick_revision": [],
            "knowledge_gaps": [],
            "sources": [],
        }
    )
    output = tmp_path / "Study_Guide.pdf"
    PDFService().generate(guide, output)
    assert "Visual Mental Models" not in _pdf_text(output)


def _pdf_text(path: Path) -> str:
    import pymupdf

    with pymupdf.open(path) as document:
        return "\n".join(page.get_text() for page in document)
