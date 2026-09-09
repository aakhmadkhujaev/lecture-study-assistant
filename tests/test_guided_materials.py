"""Focused storage and UI-facing service tests for Guided Material phase A."""

import sqlite3
from pathlib import Path

from config.settings import Settings

from app.services.library_service import (
    create_course,
    create_lecture,
    delete_course,
    delete_lecture,
    get_materials,
    initialize_library,
    upload_material,
)
from app.storage.database import get_connection, initialize_database


def _settings(tmp_path: Path) -> Settings:
    return Settings(
        storage_root=tmp_path / "data",
        database_path=tmp_path / "data" / "library.db",
        ai_api_key=None,
        ai_model="",
    )


def test_existing_material_records_default_to_original(tmp_path: Path) -> None:
    database_path = tmp_path / "legacy.db"
    with sqlite3.connect(database_path) as connection:
        connection.executescript(
            """
            CREATE TABLE courses (id INTEGER PRIMARY KEY, name TEXT NOT NULL, created_at TEXT NOT NULL);
            CREATE TABLE lectures (id INTEGER PRIMARY KEY, course_id INTEGER NOT NULL, title TEXT NOT NULL, created_at TEXT NOT NULL);
            CREATE TABLE materials (
                id INTEGER PRIMARY KEY,
                lecture_id INTEGER NOT NULL,
                original_filename TEXT NOT NULL,
                stored_path TEXT NOT NULL,
                uploaded_at TEXT NOT NULL
            );
            INSERT INTO materials VALUES (1, 1, 'lecture.pdf', 'courses/C/L/Original/lecture.pdf', 'now');
            """
        )

    initialize_database(database_path)

    with get_connection(database_path) as connection:
        row = connection.execute(
            "SELECT material_type FROM materials WHERE id = 1"
        ).fetchone()
    assert row["material_type"] == "original"


def test_original_and_guided_materials_use_separate_directories(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    initialize_library(settings)
    course = create_course(settings, "Algorithms")
    lecture = create_lecture(settings, course.id, "Lecture 1")

    original = upload_material(settings, lecture.id, "notes.pdf", b"original")
    guided = upload_material(
        settings, lecture.id, "notes.pdf", b"guided", material_type="guided"
    )

    assert original.material_type == "original"
    assert guided.material_type == "guided"
    assert original.stored_path.endswith("/Original/notes.pdf")
    assert guided.stored_path.endswith("/Guided_Material/notes.pdf")
    assert (settings.storage_root / original.stored_path).read_bytes() == b"original"
    assert (settings.storage_root / guided.stored_path).read_bytes() == b"guided"


def test_duplicate_filenames_are_collision_safe_per_category(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    initialize_library(settings)
    course = create_course(settings, "Algorithms")
    lecture = create_lecture(settings, course.id, "Lecture 1")

    first = upload_material(settings, lecture.id, "chapter.pdf", b"one", "guided")
    second = upload_material(settings, lecture.id, "chapter.pdf", b"two", "guided")
    original = upload_material(settings, lecture.id, "chapter.pdf", b"three")

    assert first.stored_path.endswith("/Guided_Material/chapter.pdf")
    assert second.stored_path.endswith("/Guided_Material/chapter (1).pdf")
    assert original.stored_path.endswith("/Original/chapter.pdf")


def test_materials_can_be_listed_by_category_and_legacy_upload_still_works(
    tmp_path: Path,
) -> None:
    settings = _settings(tmp_path)
    initialize_library(settings)
    course = create_course(settings, "Algorithms")
    lecture = create_lecture(settings, course.id, "Lecture 1")
    upload_material(settings, lecture.id, "original.pdf", b"original")
    upload_material(settings, lecture.id, "guided.pdf", b"guided", "guided")

    assert [item.original_filename for item in get_materials(settings, lecture.id, "original")] == [
        "original.pdf"
    ]
    assert [item.original_filename for item in get_materials(settings, lecture.id, "guided")] == [
        "guided.pdf"
    ]
    assert len(get_materials(settings, lecture.id)) == 2


def test_deleting_lecture_and_course_removes_category_files_and_metadata(
    tmp_path: Path,
) -> None:
    settings = _settings(tmp_path)
    initialize_library(settings)
    course = create_course(settings, "Algorithms")
    lecture = create_lecture(settings, course.id, "Lecture 1")
    upload_material(settings, lecture.id, "original.pdf", b"original")
    upload_material(settings, lecture.id, "guided.pdf", b"guided", "guided")
    lecture_directory = settings.storage_root / "courses" / course.name / lecture.title

    delete_lecture(settings, lecture.id)
    assert not lecture_directory.exists()
    assert get_materials(settings, lecture.id) == []

    second_lecture = create_lecture(settings, course.id, "Lecture 2")
    upload_material(settings, second_lecture.id, "guided.pdf", b"guided", "guided")
    course_directory = settings.storage_root / "courses" / course.name
    delete_course(settings, course.id)
    assert not course_directory.exists()