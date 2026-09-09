"""Application services for the course and lecture library."""

import shutil
import sqlite3
from pathlib import Path
from typing import BinaryIO

from config.settings import Settings

from app.storage.database import get_connection, initialize_database
from app.storage.filesystem import (
    ensure_lecture_directory,
    lecture_directory,
    store_material,
    validate_directory_name,
)
from app.storage.models import Course, Lecture, Material
from app.storage.repositories import (
    get_course,
    get_lecture,
    get_material,
    insert_course,
    insert_lecture,
    insert_material,
    list_courses,
    list_lectures,
    list_materials,
)
from app.processors.factory import extract_document
from app.processors.models import Document, DocumentProcessingError
from app.processors.ocr import OCRProvider

ALLOWED_MATERIAL_EXTENSIONS = {".pdf", ".docx", ".pptx"}
ALLOWED_MATERIAL_TYPES = {"original", "guided"}


class LibraryError(Exception):
    """Base class for expected library errors shown to users."""


class DuplicateEntityError(LibraryError):
    """Raised when a course or lecture name already exists."""


class EntityNotFoundError(LibraryError):
    """Raised when a requested course or lecture does not exist."""


class UnsupportedMaterialError(LibraryError):
    """Raised when an uploaded file is outside the V1 allowlist."""


class PersistenceError(LibraryError):
    """Raised when SQLite cannot complete an operation."""


class FileStorageError(LibraryError):
    """Raised when local filesystem storage cannot complete an operation."""


class ExtractionError(LibraryError):
    """Raised when a stored document cannot be extracted."""


def initialize_library(settings: Settings) -> None:
    """Initialize SQLite and the root directory for local materials."""
    try:
        initialize_database(settings.database_path)
        (settings.storage_root / "courses").mkdir(parents=True, exist_ok=True)
    except OSError as error:
        raise FileStorageError(f"Could not initialize local storage: {error}") from error
    except sqlite3.Error as error:
        raise PersistenceError(f"Could not initialize the database: {error}") from error


def get_courses(settings: Settings) -> list[Course]:
    """Return all courses from SQLite."""
    try:
        with get_connection(settings.database_path) as connection:
            return list_courses(connection)
    except sqlite3.Error as error:
        raise PersistenceError(f"Could not load courses: {error}") from error


def get_course_by_id(settings: Settings, course_id: int) -> Course:
    """Return one course or raise a user-facing not-found error."""
    try:
        with get_connection(settings.database_path) as connection:
            course = get_course(connection, course_id)
    except sqlite3.Error as error:
        raise PersistenceError(f"Could not load the course: {error}") from error
    if course is None:
        raise EntityNotFoundError("That course no longer exists.")
    return course


def create_course(settings: Settings, name: str) -> Course:
    """Create a course and its stable filesystem directory."""
    try:
        course_name = validate_directory_name(name)
    except ValueError as error:
        raise LibraryError(str(error)) from error

    try:
        with get_connection(settings.database_path) as connection:
            course = insert_course(connection, course_name)
    except sqlite3.IntegrityError as error:
        raise DuplicateEntityError(
            f'A course named "{course_name}" already exists.'
        ) from error
    except sqlite3.Error as error:
        raise PersistenceError(f"Could not create the course: {error}") from error

    try:
        (settings.storage_root / "courses" / course.name).mkdir(
            parents=True,
            exist_ok=True,
        )
    except OSError as error:
        _delete_course_record(settings, course.id)
        raise FileStorageError(f"Could not create the course folder: {error}") from error
    return course


def delete_course(settings: Settings, course_id: int) -> None:
    """Delete a course, its lectures, metadata, and stored files."""
    course = get_course_by_id(settings, course_id)
    directory = settings.storage_root / "courses" / course.name
    try:
        with get_connection(settings.database_path) as connection:
            connection.execute("BEGIN")
            connection.execute("DELETE FROM courses WHERE id = ?", (course.id,))
            if directory.exists():
                shutil.rmtree(directory)
            connection.commit()
    except (sqlite3.Error, OSError) as error:
        raise LibraryError(f"Could not delete the course: {error}") from error


def get_lectures(settings: Settings, course_id: int) -> list[Lecture]:
    """Return lectures for a course from SQLite."""
    try:
        with get_connection(settings.database_path) as connection:
            return list_lectures(connection, course_id)
    except sqlite3.Error as error:
        raise PersistenceError(f"Could not load lectures: {error}") from error


def get_lecture_by_id(settings: Settings, lecture_id: int) -> Lecture:
    """Return one lecture or raise a user-facing not-found error."""
    try:
        with get_connection(settings.database_path) as connection:
            lecture = get_lecture(connection, lecture_id)
    except sqlite3.Error as error:
        raise PersistenceError(f"Could not load the lecture: {error}") from error
    if lecture is None:
        raise EntityNotFoundError("That lecture no longer exists.")
    return lecture


def create_lecture(settings: Settings, course_id: int, title: str) -> Lecture:
    """Create a lecture and reuse/create its stable directory."""
    try:
        lecture_title = validate_directory_name(title)
    except ValueError as error:
        raise LibraryError(str(error)) from error

    course = get_course_by_id(settings, course_id)
    try:
        with get_connection(settings.database_path) as connection:
            lecture = insert_lecture(connection, course.id, lecture_title)
    except sqlite3.IntegrityError as error:
        raise DuplicateEntityError(
            f'A lecture named "{lecture_title}" already exists in this course.'
        ) from error
    except sqlite3.Error as error:
        raise PersistenceError(f"Could not create the lecture: {error}") from error

    try:
        ensure_lecture_directory(settings.storage_root, course.name, lecture.title)
    except OSError as error:
        _delete_lecture_record(settings, lecture.id)
        raise FileStorageError(f"Could not create the lecture folder: {error}") from error
    return lecture


def delete_lecture(settings: Settings, lecture_id: int) -> None:
    """Delete a lecture, its metadata, and stored files."""
    lecture = get_lecture_by_id(settings, lecture_id)
    course = get_course_by_id(settings, lecture.course_id)
    directory = lecture_directory(settings.storage_root, course.name, lecture.title)
    try:
        with get_connection(settings.database_path) as connection:
            connection.execute("BEGIN")
            connection.execute("DELETE FROM lectures WHERE id = ?", (lecture.id,))
            if directory.exists():
                shutil.rmtree(directory)
            connection.commit()
    except (sqlite3.Error, OSError) as error:
        raise LibraryError(f"Could not delete the lecture: {error}") from error


def get_materials(
    settings: Settings,
    lecture_id: int,
    material_type: str | None = None,
) -> list[Material]:
    """Return materials for a lecture from SQLite."""
    try:
        with get_connection(settings.database_path) as connection:
            materials = list_materials(connection, lecture_id)
            if material_type is not None:
                materials = [item for item in materials if item.material_type == material_type]
            return materials
    except sqlite3.Error as error:
        raise PersistenceError(f"Could not load materials: {error}") from error


def get_material_by_id(settings: Settings, material_id: int) -> Material:
    """Return one material or raise a user-facing not-found error."""
    try:
        with get_connection(settings.database_path) as connection:
            material = get_material(connection, material_id)
    except sqlite3.Error as error:
        raise PersistenceError(f"Could not load the material: {error}") from error
    if material is None:
        raise EntityNotFoundError("That material no longer exists.")
    return material


def extract_material_content(
    settings: Settings,
    material_id: int,
    ocr_provider: OCRProvider | None = None,
) -> Document:
    """Extract structured content from an existing stored material."""
    material = get_material_by_id(settings, material_id)
    file_path = settings.storage_root / material.stored_path
    try:
        return extract_document(file_path, ocr_provider=ocr_provider)
    except DocumentProcessingError as error:
        raise ExtractionError(str(error)) from error
    except OSError as error:
        raise FileStorageError(f"Could not access the stored material: {error}") from error


def upload_material(
    settings: Settings,
    lecture_id: int,
    original_filename: str,
    content: bytes | BinaryIO,
    material_type: str = "original",
) -> Material:
    """Store one supported material and persist its metadata."""
    extension = Path(original_filename).suffix.lower()
    if extension not in ALLOWED_MATERIAL_EXTENSIONS:
        allowed = ", ".join(sorted(ALLOWED_MATERIAL_EXTENSIONS))
        raise UnsupportedMaterialError(
            f"Unsupported file type. Supported types are: {allowed}."
        )
    if material_type not in ALLOWED_MATERIAL_TYPES:
        raise LibraryError("Material type must be 'original' or 'guided'.")

    lecture = get_lecture_by_id(settings, lecture_id)
    course = get_course_by_id(settings, lecture.course_id)
    file_content = content.read() if hasattr(content, "read") else content
    if not isinstance(file_content, bytes):
        raise LibraryError("The uploaded file could not be read.")

    try:
        stored_path = store_material(
            settings.storage_root,
            course.name,
            lecture.title,
            original_filename,
            file_content,
            material_type,
        )
    except (OSError, ValueError) as error:
        raise FileStorageError(f"Could not store the uploaded file: {error}") from error

    try:
        with get_connection(settings.database_path) as connection:
            return insert_material(
                connection,
                lecture.id,
                original_filename,
                stored_path,
                material_type,
            )
    except sqlite3.Error as error:
        stored_file = settings.storage_root / stored_path
        stored_file.unlink(missing_ok=True)
        raise PersistenceError(f"Could not save material metadata: {error}") from error


def _delete_course_record(settings: Settings, course_id: int) -> None:
    with get_connection(settings.database_path) as connection:
        connection.execute("DELETE FROM courses WHERE id = ?", (course_id,))


def _delete_lecture_record(settings: Settings, lecture_id: int) -> None:
    with get_connection(settings.database_path) as connection:
        connection.execute("DELETE FROM lectures WHERE id = ?", (lecture_id,))
