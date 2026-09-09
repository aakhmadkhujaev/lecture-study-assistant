"""Application integration for rendering persisted study guides."""

from pathlib import Path

from config.settings import Settings

from app.ai.service import StudyGuidePersistenceError, load_study_guide, study_guide_path
from app.pdf.renderer import PDFService
from app.services.library_service import get_course_by_id, get_lecture_by_id


def study_guide_pdf_path(settings: Settings, lecture_id: int) -> Path:
    return study_guide_path(settings, lecture_id).with_name("Study_Guide.pdf")


def generate_lecture_study_guide_pdf(
    settings: Settings,
    lecture_id: int,
    overwrite: bool = False,
) -> Path:
    guide = load_study_guide(settings, lecture_id)
    if guide is None:
        raise StudyGuidePersistenceError(
            "Generate a Study Guide before creating its PDF."
        )
    lecture = get_lecture_by_id(settings, lecture_id)
    course = get_course_by_id(settings, lecture.course_id)
    return PDFService().generate(
        guide,
        study_guide_pdf_path(settings, lecture_id),
        course.name,
        overwrite,
    )