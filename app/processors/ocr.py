"""Local OCR provider abstraction and Tesseract implementation."""

from pathlib import Path
from typing import Protocol

from PIL import Image, ImageEnhance, ImageOps


class OCRProcessingError(Exception):
    """Raised when OCR cannot process an image."""


class OCRProvider(Protocol):
    """Interface used by document processors for local OCR."""

    def extract_text(self, image: Image.Image) -> str:
        """Extract text from one rendered image."""


class LocalOCRProvider:
    """Run offline OCR through the locally installed Tesseract executable."""

    def __init__(self, executable_path: str | Path | None = None) -> None:
        try:
            import pytesseract
        except ImportError as error:
            raise OCRProcessingError(
                "Python OCR support is missing. Install the project requirements."
            ) from error
        self._pytesseract = pytesseract
        if executable_path is not None:
            self._pytesseract.pytesseract.tesseract_cmd = str(executable_path)

    def extract_text(self, image: Image.Image) -> str:
        """Preprocess an image and extract English text locally."""
        try:
            prepared = _preprocess_image(image)
            return self._pytesseract.image_to_string(prepared, lang="eng").strip()
        except self._pytesseract.pytesseract.TesseractNotFoundError as error:
            raise OCRProcessingError(
                "Tesseract OCR is not installed or is not available on PATH. "
                "Install Tesseract and restart the application."
            ) from error
        except Exception as error:
            raise OCRProcessingError(f"OCR could not process the image: {error}") from error


def _preprocess_image(image: Image.Image) -> Image.Image:
    """Apply small, general-purpose preprocessing for lecture screenshots."""
    grayscale = ImageOps.grayscale(image)
    contrast = ImageEnhance.Contrast(grayscale).enhance(1.5)
    return contrast.resize((contrast.width * 2, contrast.height * 2))
