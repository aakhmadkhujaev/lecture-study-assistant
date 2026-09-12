"""Flowable builders for individual StudyGuide sections."""

from reportlab.platypus import KeepTogether, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.units import mm

from app.ai.schemas import StudyGuide
from app.visuals.renderer import render_visual_flowables

from app.pdf.styles import ANSWER_STYLE, QUESTION_STYLE, SUBSECTION_STYLE
from app.pdf.utils import add_reference, bullet_items, paragraph, section_heading


def render_lecture_overview(guide: StudyGuide) -> list[object]:
    if not guide.lecture_overview.strip():
        return []
    return [section_heading("Lecture Overview"), paragraph(guide.lecture_overview)]


def render_learning_objectives(guide: StudyGuide) -> list[object]:
    if not guide.learning_objectives:
        return []
    return [section_heading("Learning Objectives"), *bullet_items(guide.learning_objectives)]


def render_mental_model(guide: StudyGuide) -> list[object]:
    mental_model = guide.mental_model
    if not _has_meaningful_content(
        mental_model.core_idea,
        mental_model.components,
        mental_model.relationships,
        mental_model.how_it_works,
        mental_model.key_takeaway,
    ):
        return []
    story: list[object] = [section_heading("Mental Model")]
    if mental_model.core_idea.strip():
        story.extend([paragraph("Core idea", SUBSECTION_STYLE), paragraph(mental_model.core_idea)])
    if mental_model.components:
        story.extend([paragraph("Components", SUBSECTION_STYLE), *bullet_items(_meaningful_items(mental_model.components))])
    if mental_model.relationships:
        story.extend([paragraph("Relationships", SUBSECTION_STYLE), *bullet_items(_meaningful_items(mental_model.relationships))])
    if mental_model.how_it_works.strip():
        story.extend([paragraph("How it works", SUBSECTION_STYLE), paragraph(mental_model.how_it_works)])
    if mental_model.key_takeaway.strip():
        story.extend([paragraph("Key takeaway", SUBSECTION_STYLE), paragraph(mental_model.key_takeaway)])
    return story


def render_key_concepts(guide: StudyGuide) -> list[object]:
    if not guide.key_concepts:
        return []
    story: list[object] = [section_heading("Key Concepts")]
    for item in guide.key_concepts:
        content: list[object] = [paragraph(f"{item.name} ({_priority_label(item.importance)})", SUBSECTION_STYLE)]
        content.append(paragraph(item.definition))
        content.append(paragraph(item.explanation))
        if item.example:
            content.append(paragraph(f"Example: {item.example}"))
        if item.use_when:
            content.append(paragraph(f"Use when: {item.use_when}"))
        if item.avoid_when:
            content.append(paragraph(f"Avoid when: {item.avoid_when}"))
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


def render_real_world_applications(guide: StudyGuide) -> list[object]:
    applications = [
        application
        for application in guide.real_world_applications
        if _has_meaningful_content(
            application.title,
            application.problem,
            application.solution,
            application.why_this_concept,
            application.impact,
        )
    ]
    if not applications:
        return []
    story: list[object] = [section_heading("Real-World Applications")]
    for application in applications:
        content = [paragraph(application.title, SUBSECTION_STYLE)]
        content.extend([
            paragraph(f"Problem: {application.problem}"),
            paragraph(f"Solution: {application.solution}"),
            paragraph(f"Why this concept: {application.why_this_concept}"),
            paragraph(f"Impact: {application.impact}"),
        ])
        add_reference(content, application.source_references)
        story.append(KeepTogether(content))
    return story


def render_engineering_connections(guide: StudyGuide) -> list[object]:
    connections = [
        connection
        for connection in guide.engineering_connections
        if _has_meaningful_content(
            connection.concept,
            connection.real_world_problem,
            connection.engineering_decision,
            connection.implementation,
            connection.trade_offs,
        )
    ]
    if not connections:
        return []
    story: list[object] = [section_heading("Engineering Connections")]
    for connection in connections:
        content = [paragraph(connection.concept, SUBSECTION_STYLE)]
        content.extend([
            paragraph(f"Real-world problem: {connection.real_world_problem}"),
            paragraph(f"Engineering decision: {connection.engineering_decision}"),
            paragraph(f"Implementation: {connection.implementation}"),
            paragraph(f"Trade-offs: {connection.trade_offs}"),
        ])
        add_reference(content, connection.source_references)
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
            content = [paragraph(item.name, QUESTION_STYLE), paragraph(item.definition)]
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


def _has_meaningful_content(*values: str | list[str]) -> bool:
    return any(
        value.strip() if isinstance(value, str) else any(item.strip() for item in value)
        for value in values
    )


def _meaningful_items(values: list[str]) -> list[str]:
    return [value for value in values if value.strip()]

