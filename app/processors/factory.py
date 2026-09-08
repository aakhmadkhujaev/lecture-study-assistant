"""Processor selection by document extension."""

from pathlib import Path

from app.processors.docx_processor import DOCXProcessor
from app.processors.models import Document, DocumentProcessor, UnsupportedDocumentError
from app.processors.ocr import OCRProvider
from app.processors.pdf_processor import PDFProcessor
from app.processors.pptx_processor import PPTXProcessor


_PROCESSORS: dict[str, type[DocumentProcessor]] = {
    PDFProcessor.supported_extension: PDFProcessor,
    DOCXProcessor.supported_extension: DOCXProcessor,
    PPTXProcessor.supported_extension: PPTXProcessor,
}


def get_processor(
    file_path: Path,
    ocr_provider: OCRProvider | None = None,
) -> DocumentProcessor:
    """Return the parser registered for a file extension."""
    extension = file_path.suffix.lower()
    processor_class = _PROCESSORS.get(extension)
    if processor_class is None:
        supported = ", ".join(sorted(_PROCESSORS))
        raise UnsupportedDocumentError(
            f"Unsupported document type: {extension or '[no extension]'}. "
            f"Supported types are: {supported}."
        )
    if extension in {PDFProcessor.supported_extension, PPTXProcessor.supported_extension}:
        return processor_class(ocr_provider=ocr_provider)
    return processor_class()


def extract_document(
    file_path: Path,
    ocr_provider: OCRProvider | None = None,
) -> Document:
    """Select the correct parser and extract a document."""
    return get_processor(file_path, ocr_provider=ocr_provider).process(file_path)
