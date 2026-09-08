"""Integration test for extracting a stored library material."""

from pathlib import Path

from config.settings import Settings

from app.services.library_service import (
    create_course,
    create_lecture,
    extract_material_content,
    initialize_library,
    upload_material,
)


def test_extract_material_uses_stored_metadata_path(tmp_path: Path) -> None:
    settings = Settings(
        storage_root=tmp_path / "data",
        database_path=tmp_path / "data" / "library.db",
        ai_api_key=None,
        ai_model="",
    )
    initialize_library(settings)
    course = create_course(settings, "Computer Science")
    lecture = create_lecture(settings, course.id, "Lecture 01")
    material = upload_material(
        settings,
        lecture.id,
        "stored.pdf",
        _pdf_bytes("Stored lecture text"),
    )

    extracted = extract_material_content(settings, material.id)

    assert extracted.filename == "stored.pdf"
    assert extracted.sections[0].source_type == "page"
    assert extracted.sections[0].source_index == 1
    assert extracted.sections[0].text == "Stored lecture text"


def _pdf_bytes(text: str) -> bytes:
    import pymupdf

    document = pymupdf.open()
    page = document.new_page()
    page.insert_text((72, 72), text)
    content = document.tobytes()
    document.close()
    return content
