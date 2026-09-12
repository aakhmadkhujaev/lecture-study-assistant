"""Focused tests for downloading the persisted study-guide PDF."""

from pathlib import Path

from config.settings import Settings

from app.pdf.service import study_guide_pdf_path
from app.services.library_service import create_course, create_lecture, initialize_library
from app.ui import library


class StreamlitRecorder:
    def __init__(self) -> None:
        self.downloads: list[dict[str, object]] = []
        self.info_messages: list[str] = []

    def download_button(self, label: str, **kwargs: object) -> None:
        self.downloads.append({"label": label, **kwargs})

    def info(self, message: str) -> None:
        self.info_messages.append(message)

    def error(self, message: str) -> None:
        raise AssertionError(message)


def test_existing_pdf_is_downloadable_with_expected_filename(
    tmp_path: Path,
    monkeypatch,
) -> None:
    pdf_path = tmp_path / "Study_Guide.pdf"
    pdf_bytes = b"%PDF-existing-guide"
    pdf_path.write_bytes(pdf_bytes)
    recorder = StreamlitRecorder()
    monkeypatch.setattr(library, "st", recorder)

    library._render_pdf_download(pdf_path)

    assert recorder.downloads == [
        {
            "label": "Download Study Guide PDF",
            "data": pdf_bytes,
            "file_name": "Study_Guide.pdf",
            "mime": "application/pdf",
            "key": f"download-study-guide-pdf-{pdf_path}",
        }
    ]


def test_pdf_path_resolves_to_canonical_lecture_directory(tmp_path: Path) -> None:
    settings = Settings(
        storage_root=tmp_path / "data",
        database_path=tmp_path / "data" / "library.db",
        ai_api_key=None,
        ai_model="",
    )
    initialize_library(settings)
    course = create_course(settings, "Algorithms")
    lecture = create_lecture(settings, course.id, "Lecture 1")

    assert study_guide_pdf_path(settings, lecture.id) == (
        tmp_path / "data" / "courses" / "Algorithms" / "Lecture 1" / "Study_Guide.pdf"
    )


def test_missing_pdf_shows_generation_message_without_download(
    tmp_path: Path,
    monkeypatch,
) -> None:
    recorder = StreamlitRecorder()
    monkeypatch.setattr(library, "st", recorder)

    library._render_pdf_download(tmp_path / "Study_Guide.pdf")

    assert recorder.downloads == []
    assert recorder.info_messages == [
        "Generate the PDF first to download the Study Guide PDF."
    ]