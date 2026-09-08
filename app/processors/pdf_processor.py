"""PDF text extraction, preserving page traceability."""

from pathlib import Path

import pymupdf
from PIL import Image
from io import BytesIO

from app.processors.models import (
    Document,
    DocumentNotFoundError,
    DocumentProcessingError,
    DocumentProcessor,
    DocumentReadError,
    EmptyDocumentError,
    Section,
)
from app.processors.ocr import LocalOCRProvider, OCRProcessingError, OCRProvider


class PDFProcessor(DocumentProcessor):
    """Extract PDF text with OCR fallback for image-based pages."""

    supported_extension = ".pdf"

    def __init__(self, ocr_provider: OCRProvider | None = None) -> None:
        self._ocr_provider = ocr_provider

    def process(self, file_path: Path) -> Document:
        _require_file(file_path)
        sections: list[Section] = []
        used_ocr = False
        try:
            with pymupdf.open(file_path) as pdf_document:
                for page_number, page in enumerate(pdf_document, start=1):
                    text = page.get_text("text").strip()
                    extraction_method = "text"
                    if not text:
                        pixmap = page.get_pixmap(matrix=pymupdf.Matrix(2, 2), alpha=False)
                        image = Image.open(BytesIO(pixmap.tobytes("png")))
                        try:
                            text = self._ocr(image)
                        except OCRProcessingError as error:
                            raise EmptyDocumentError(
                                "The page contains no extractable text and may be scanned or image-based. "
                                "OCR is unavailable. "
                                f"{error}"
                            ) from error
                        used_ocr = True
                        extraction_method = "ocr"
                    if not text:
                        raise EmptyDocumentError(
                            f"Page {page_number} contains no extractable text and OCR could not detect readable content."
                        )
                    sections.append(
                        Section(
                            source_index=page_number,
                            source_type="page",
                            text=text,
                            extraction_method=extraction_method,
                        )
                    )
        except (pymupdf.FileDataError, OSError, RuntimeError) as error:
            raise DocumentReadError(f"Could not read PDF document: {error}") from error

        return Document(
            file_path.name,
            self.supported_extension,
            tuple(sections),
            extraction_method="ocr" if used_ocr else "text",
        )

    def _ocr(self, image: Image.Image) -> str:
        provider = self._ocr_provider or LocalOCRProvider()
        try:
            return provider.extract_text(image).strip()
        except OCRProcessingError:
            raise
        except Exception as error:
            raise DocumentReadError(f"PDF OCR failed: {error}") from error


def _require_file(file_path: Path) -> None:
    if not file_path.exists() or not file_path.is_file():
        raise DocumentNotFoundError(f"Document does not exist: {file_path}")
