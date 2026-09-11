"""Flowable builders for individual StudyGuide sections."""

from reportlab.platypus import KeepTogether, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.units import mm

from app.ai.schemas import StudyGuide
from app.visuals.renderer import render_visual_flowables

from app.pdf.styles import ANSWER_STYLE, QUESTION_STYLE, SUBSECTION_STYLE
from app.pdf.utils import add_reference, bullet_items, paragraph, section_heading


def render_lecture_overview(guide: StudyGuide) -> list[object]:
    if not guide.overview.strip():
        return []
    return [section_heading("Lecture Overview"), paragraph(guide.overview)]


def render_learning_objectives(guide: StudyGuide) -> list[object]:
    if not guide.learning_objectives:
        return []
    return [section_heading("Learning Objectives"), *bullet_items(guide.learning_objectives)]


def render_key_concepts(guide: StudyGuide) -> list[object]:
    if not guide.key_concepts:
        return []
    story: list[object] = [section_heading("Key Concepts")]
    for item in guide.key_concepts:
        content: list[object] = [paragraph(f"{item.concept} ({_priority_label(item.importance)})", SUBSECTION_STYLE)]
        content.append(paragraph(item.simple_explanation))
        content.extend(bullet_items(item.important_points))
        if item.example:
            content.append(paragraph(f"Example: {item.example}"))
        if item.remember:
            content.append(paragraph(f"Remember: {item.remember}"))
        add_reference(content, item.source_references)
        story.append(KeepTogether(content))
    return story


def render_definitions(guide: StudyGuide) -> list[object]:
    if not guide.definitions:
        return []
    story: list[object] = [section_heading("Important Definitions")]
    for item in guide.definitions:
        content = [paragraph(item.term, SUBSECTION_STYLE), paragraph(item.simple_definition)]
        add_reference(content, item.source_references)
        story.append(KeepTogether(content))
    return story


def render_formulas_algorithms(guide: StudyGuide) -> list[object]:
    if not guide.formulas:
        return []
    story: list[object] = [section_heading("Formulas & Algorithms")]
    for item in guide.formulas:
        content = [paragraph(item.formula, SUBSECTION_STYLE), paragraph(item.meaning)]
        add_reference(content, item.source_references)
        story.append(KeepTogether(content))
    return story


def render_revision_priorities(guide: StudyGuide) -> list[object]:
    if not guide.key_concepts and not guide.exam_topics:
        return []
    story: list[object] = [section_heading("Important for Revision")]
    for importance in ("must_know", "important", "supporting"):
        items = [item for item in guide.key_concepts if item.importance == importance]
        if not items:
            continue
        story.append(paragraph(_priority_label(importance), SUBSECTION_STYLE))
        for item in items:
            content = [paragraph(item.concept, QUESTION_STYLE), paragraph(item.simple_explanation)]
            add_reference(content, item.source_references)
            story.append(KeepTogether(content))
    if guide.exam_topics:
        story.append(paragraph("Additional Revision Topics", SUBSECTION_STYLE))
        for item in guide.exam_topics:
            content = [paragraph(item.topic, QUESTION_STYLE), paragraph(item.why_important)]
            add_reference(content, item.source_references)
            story.append(KeepTogether(content))
    return story


def render_common_confusions(guide: StudyGuide) -> list[object]:
    if not guide.common_confusions:
        return []
    story: list[object] = [section_heading("Common Confusions")]
    for item in guide.common_confusions:
        content = [paragraph(item.topic, SUBSECTION_STYLE), paragraph(f"Confusion: {item.confusion}"), paragraph(f"Clarification: {item.clarification}")]
        add_reference(content, item.source_references)
        story.append(KeepTogether(content))
    return story


def render_practice_questions(guide: StudyGuide) -> list[object]:
    if not guide.practice_questions:
        return []
    story: list[object] = [section_heading("Practice Questions")]
    for item in guide.practice_questions:
        content = [
            paragraph(f"{item.question_type.replace('_', ' ').title()}: {item.question}", QUESTION_STYLE),
            paragraph(f"Model answer: {item.model_answer}", ANSWER_STYLE),
        ]
        add_reference(content, item.source_references)
        story.append(KeepTogether(content))
    return story


def render_quick_revision(guide: StudyGuide) -> list[object]:
    if not guide.quick_revision:
        return []
    return [section_heading("Quick Revision"), *bullet_items(guide.quick_revision)]


def render_knowledge_gaps(guide: StudyGuide) -> list[object]:
    if not guide.knowledge_gaps:
        return []
    story: list[object] = [section_heading("Knowledge Gaps")]
    for item in guide.knowledge_gaps:
        content = [paragraph(item.topic, SUBSECTION_STYLE), paragraph(item.reason), paragraph(f"Missing: {item.what_is_missing}"), paragraph(f"Recommended action: {item.recommended_action}")]
        add_reference(content, item.source_references)
        story.append(KeepTogether(content))
    return story


def render_visual_models(guide: StudyGuide) -> list[object]:
    if not guide.visual_models:
        return []
    story: list[object] = [section_heading("Visual Mental Models")]
    for visual in guide.visual_models:
        story.extend(render_visual_flowables(visual))
    return story


def render_sources(guide: StudyGuide) -> list[object]:
    if not guide.sources:
        return []
    rows = [[paragraph("Filename", SUBSECTION_STYLE), paragraph("Location", SUBSECTION_STYLE)]]
    rows.extend(
        [paragraph(source.filename), paragraph(f"{source.source_type} {source.source_index}")]
        for source in guide.sources
    )
    table = Table(rows, colWidths=[None, 35 * mm])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E7EEF2")),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#B9C8D0")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    return [section_heading("Sources"), table]


def _priority_label(value: str) -> str:
    return {"must_know": "Must Know", "important": "Important", "supporting": "Supporting"}.get(value, value)

