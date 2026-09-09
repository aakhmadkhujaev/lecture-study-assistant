"""Small ReportLab helpers shared by study-guide sections."""

from xml.sax.saxutils import escape

from reportlab.platypus import Paragraph, Spacer

from app.ai.schemas import SourceReference

from app.pdf.styles import BODY_STYLE, BULLET_STYLE, SECTION_STYLE, SMALL_STYLE


def safe_text(value: object) -> str:
    """Escape plain model text for ReportLab's paragraph markup."""
    return escape(str(value)).replace("\n", "<br/>")


def paragraph(value: object, style=BODY_STYLE) -> Paragraph:
    return Paragraph(safe_text(value), style)


def rich_paragraph(value: str, style=BODY_STYLE) -> Paragraph:
    return Paragraph(value, style)


def section_heading(title: str) -> Paragraph:
    return paragraph(title, SECTION_STYLE)


def bullet_items(values: list[str]) -> list[Paragraph]:
    return [Paragraph(f"&bull; {safe_text(value)}", BULLET_STYLE) for value in values]


def references_text(references: list[SourceReference]) -> str:
    return "; ".join(
        f"{reference.filename} - {reference.source_type} {reference.source_index}"
        for reference in references
    )


def reference_flowable(references: list[SourceReference]) -> Paragraph | None:
    if not references:
        return None
    return paragraph(f"Sources: {references_text(references)}", SMALL_STYLE)


def add_reference(story: list[object], references: list[SourceReference]) -> None:
    flowable = reference_flowable(references)
    if flowable is not None:
        story.append(flowable)


def gap() -> Spacer:
    return Spacer(1, 4)