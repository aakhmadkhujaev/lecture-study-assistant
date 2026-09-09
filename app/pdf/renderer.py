"""Presentation-only ReportLab renderer for validated study guides."""

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.ai.schemas import StudyGuide

from app.pdf.sections import (
    render_common_confusions,
    render_definitions,
    render_formulas_algorithms,
    render_key_concepts,
    render_knowledge_gaps,
    render_learning_objectives,
    render_lecture_overview,
    render_practice_questions,
    render_quick_revision,
    render_revision_priorities,
    render_sources,
)
from app.pdf.styles import FONT_NAME, METADATA_LABEL_STYLE, PAGE_MARGINS, PAGE_SIZE, SUBTITLE_STYLE, TITLE_STYLE
from app.pdf.utils import paragraph


class PDFService:
    """Generate a PDF from an already validated StudyGuide model."""

    def generate(
        self,
        study_guide: StudyGuide,
        output_path: Path,
        course_name: str | None = None,
        overwrite: bool = False,
    ) -> Path:
        if output_path.exists() and not overwrite:
            raise FileExistsError(f"The PDF already exists: {output_path}")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        document = SimpleDocTemplate(
            str(output_path),
            pagesize=PAGE_SIZE,
            title="Lecture Study Guide",
            author="Lecture Study Assistant",
            **PAGE_MARGINS,
        )
        document.build(_build_story(study_guide, output_path, course_name), onFirstPage=_draw_page, onLaterPages=_draw_page)
        return output_path


def generate_study_guide_pdf(
    study_guide: StudyGuide,
    output_path: Path,
    course_name: str | None = None,
    overwrite: bool = False,
) -> Path:
    """Functional entry point for presentation-only PDF generation."""
    return PDFService().generate(study_guide, output_path, course_name, overwrite)


def _build_story(study_guide: StudyGuide, output_path: Path, course_name: str | None) -> list[object]:
    story: list[object] = [
        paragraph("Lecture Study Guide", TITLE_STYLE),
        paragraph(study_guide.lecture_title, SUBTITLE_STYLE),
    ]
    metadata = []
    if course_name:
        metadata.append([Paragraph("Course:", METADATA_LABEL_STYLE), paragraph(course_name)])
    metadata.extend([
        [Paragraph("Lecture:", METADATA_LABEL_STYLE), paragraph(study_guide.lecture_title)],
        [Paragraph("Source material:", METADATA_LABEL_STYLE), paragraph(_source_filenames(study_guide))],
        [Paragraph("Generated study guide:", METADATA_LABEL_STYLE), paragraph(output_path.name)],
    ])
    metadata_table = Table(metadata, colWidths=[34 * mm, None])
    metadata_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F1F5F6")),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#D5E0E5")),
        ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#D5E0E5")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.extend([metadata_table, Spacer(1, 8)])
    for renderer in (
        render_lecture_overview,
        render_learning_objectives,
        render_key_concepts,
        render_definitions,
        render_formulas_algorithms,
        render_revision_priorities,
        render_common_confusions,
        render_practice_questions,
        render_quick_revision,
        render_knowledge_gaps,
        render_sources,
    ):
        story.extend(renderer(study_guide))
    return story


def _source_filenames(study_guide: StudyGuide) -> str:
    filenames = list(dict.fromkeys(source.filename for source in study_guide.sources))
    return ", ".join(filenames) if filenames else "Not available"


def _draw_page(canvas: object, document: object) -> None:
    canvas.saveState()
    width, height = PAGE_SIZE
    canvas.setStrokeColor(colors.HexColor("#D5E0E5"))
    canvas.line(20 * mm, height - 14 * mm, width - 20 * mm, height - 14 * mm)
    canvas.setFont(FONT_NAME, 8)
    canvas.setFillColor(colors.HexColor("#52616B"))
    canvas.drawString(20 * mm, height - 11 * mm, "Lecture Study Assistant")
    canvas.drawRightString(width - 20 * mm, 10 * mm, f"Page {canvas.getPageNumber()}")
    canvas.restoreState()