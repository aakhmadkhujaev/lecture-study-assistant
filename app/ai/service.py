"""Study-guide generation and canonical JSON persistence for lectures."""

import json
from pathlib import Path

from config.settings import Settings

from app.ai.generator import generate_study_guide
from app.ai.openai_provider import OpenAIProvider
from app.ai.provider import LLMProvider
from app.ai.schemas import StudyGuide
from app.processors.models import Document
from app.services.library_service import (
    EntityNotFoundError,
    extract_material_content,
    get_course_by_id,
    get_lecture_by_id,
    get_materials,
)
from app.storage.filesystem import lecture_directory


class StudyGuidePersistenceError(Exception):
    """Raised when a generated guide cannot be safely persisted."""


class StudyGuideAlreadyExistsError(StudyGuidePersistenceError):
    """Raised when generation would silently replace an existing guide."""


def study_guide_path(settings: Settings, lecture_id: int) -> Path:
    """Return the canonical JSON path for a lecture's study guide."""
    lecture = get_lecture_by_id(settings, lecture_id)
    course = get_course_by_id(settings, lecture.course_id)
    return lecture_directory(settings.storage_root, course.name, lecture.title) / "Study_Guide.json"


def save_study_guide(
    settings: Settings,
    lecture_id: int,
    guide: StudyGuide,
    overwrite: bool = False,
) -> Path:
    """Persist a validated guide without silently replacing an existing artifact."""
    path = study_guide_path(settings, lecture_id)
    if path.exists() and not overwrite:
        raise StudyGuideAlreadyExistsError(
            "A study guide already exists for this lecture. Confirm regeneration to replace it."
        )
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as output_file:
            json.dump(guide.model_dump(mode="json"), output_file, ensure_ascii=False, indent=2)
            output_file.write("\n")
    except OSError as error:
        raise StudyGuidePersistenceError(
            f"Could not save the study guide: {error}"
        ) from error
    return path


def load_study_guide(settings: Settings, lecture_id: int) -> StudyGuide | None:
    """Load and validate a previously persisted guide, if present."""
    path = study_guide_path(settings, lecture_id)
    if not path.exists():
        return None
    try:
        with path.open("r", encoding="utf-8") as input_file:
            return StudyGuide.model_validate(json.load(input_file))
    except (OSError, ValueError, TypeError) as error:
        raise StudyGuidePersistenceError(
            f"The saved study guide could not be read: {error}"
        ) from error


def generate_lecture_study_guide(
    settings: Settings,
    lecture_id: int,
    provider: LLMProvider | None = None,
    overwrite: bool = False,
) -> tuple[StudyGuide, Path]:
    """Extract all lecture materials, generate a guide, and save its JSON artifact."""
    lecture = get_lecture_by_id(settings, lecture_id)
    materials = get_materials(settings, lecture.id)
    documents: list[Document] = []
    for material in materials:
        document = extract_material_content(settings, material.id)
        documents.append(
            Document(
                filename=Path(material.stored_path).name,
                file_type=document.file_type,
                sections=document.sections,
            )
        )
    active_provider = provider or OpenAIProvider(settings)
    guide = generate_study_guide(
        active_provider,
        lecture.title,
        documents,
        chunk_threshold=settings.ai_chunk_threshold,
    )
    path = save_study_guide(settings, lecture.id, guide, overwrite=overwrite)
    return guide, path
