"""Structured document extraction models."""

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class Section:
    """A traceable unit of extracted document text."""

    source_index: int
    source_type: str
    text: str
    extraction_method: str = "text"


@dataclass(frozen=True, slots=True)
class Document:
    """Structured content extracted from one source document."""

    filename: str
    file_type: str
    sections: tuple[Section, ...]
    extraction_method: str = "text"
    material_type: str = "original"


class DocumentProcessingError(Exception):
    """Base class for expected document-processing failures."""


class UnsupportedDocumentError(DocumentProcessingError):
    """Raised when no processor supports a document extension."""


class DocumentNotFoundError(DocumentProcessingError):
    """Raised when the source document does not exist or is not a file."""


class EmptyDocumentError(DocumentProcessingError):
    """Raised when a document contains no extractable text."""


class DocumentReadError(DocumentProcessingError):
    """Raised when a document is unreadable or malformed."""


class DocumentProcessor:
    """Common interface implemented by format-specific processors."""

    supported_extension: str

    def process(self, file_path: Path) -> Document:
        """Extract structured content from a document path."""
        raise NotImplementedError
