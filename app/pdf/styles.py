"""ReportLab presentation styles for study-guide PDFs."""

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont


PAGE_SIZE = A4
PAGE_MARGINS = {
    "leftMargin": 20 * mm,
    "rightMargin": 20 * mm,
    "topMargin": 22 * mm,
    "bottomMargin": 18 * mm,
}


def _register_unicode_font() -> str:
    candidates = [
        Path("C:/Windows/Fonts/arial.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
        Path("/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf"),
    ]
    for path in candidates:
        if path.exists():
            try:
                pdfmetrics.registerFont(TTFont("StudyGuideFont", str(path)))
            except (OSError, RuntimeError):
                continue
            return "StudyGuideFont"
    return "Helvetica"


FONT_NAME = _register_unicode_font()
styles = getSampleStyleSheet()
TITLE_STYLE = ParagraphStyle(
    "StudyGuideTitle",
    parent=styles["Title"],
    fontName=FONT_NAME,
    fontSize=22,
    leading=27,
    alignment=TA_CENTER,
    textColor=colors.HexColor("#17324D"),
    spaceAfter=10,
)
SUBTITLE_STYLE = ParagraphStyle(
    "StudyGuideSubtitle",
    parent=styles["Normal"],
    fontName=FONT_NAME,
    fontSize=10,
    leading=14,
    alignment=TA_CENTER,
    textColor=colors.HexColor("#52616B"),
    spaceAfter=16,
)
SECTION_STYLE = ParagraphStyle(
    "StudyGuideSection",
    parent=styles["Heading1"],
    fontName=FONT_NAME,
    fontSize=14,
    leading=18,
    textColor=colors.HexColor("#17324D"),
    spaceBefore=12,
    spaceAfter=7,
    keepWithNext=True,
)
SUBSECTION_STYLE = ParagraphStyle(
    "StudyGuideSubsection",
    parent=styles["Heading2"],
    fontName=FONT_NAME,
    fontSize=10.5,
    leading=14,
    textColor=colors.HexColor("#2C536F"),
    spaceBefore=7,
    spaceAfter=3,
    keepWithNext=True,
)
BODY_STYLE = ParagraphStyle(
    "StudyGuideBody",
    parent=styles["BodyText"],
    fontName=FONT_NAME,
    fontSize=9.5,
    leading=13.5,
    textColor=colors.HexColor("#202A30"),
    spaceAfter=5,
)
SMALL_STYLE = ParagraphStyle(
    "StudyGuideSmall",
    parent=BODY_STYLE,
    fontSize=8,
    leading=10.5,
    textColor=colors.HexColor("#52616B"),
)
BULLET_STYLE = ParagraphStyle(
    "StudyGuideBullet",
    parent=BODY_STYLE,
    leftIndent=13,
    firstLineIndent=-7,
    bulletIndent=0,
    spaceAfter=3,
)
QUESTION_STYLE = ParagraphStyle(
    "StudyGuideQuestion",
    parent=BODY_STYLE,
    fontName=FONT_NAME,
    textColor=colors.HexColor("#17324D"),
    spaceAfter=3,
)
ANSWER_STYLE = ParagraphStyle(
    "StudyGuideAnswer",
    parent=BODY_STYLE,
    leftIndent=10,
    borderPadding=5,
    backColor=colors.HexColor("#F1F5F6"),
    borderColor=colors.HexColor("#D5E0E5"),
    borderWidth=0.5,
    borderRadius=2,
    spaceAfter=8,
)
METADATA_LABEL_STYLE = ParagraphStyle(
    "StudyGuideMetadataLabel",
    parent=SMALL_STYLE,
    fontName=FONT_NAME,
    textColor=colors.HexColor("#17324D"),
)