"""Study-guide generation orchestration and validation."""

import json
from collections.abc import Iterable

from pydantic import ValidationError

from app.ai.prompts import (
    SYSTEM_PROMPT,
    build_repair_prompt,
    build_source_prompt,
    build_synthesis_prompt,
)
from app.ai.provider import AIProviderError, LLMProvider
from app.ai.schemas import SourceReference, StudyGuide
from app.processors.models import Document


class StudyGuideGenerationError(Exception):
    """Raised when a structured study guide cannot be generated safely."""


class EmptyLectureContentError(StudyGuideGenerationError):
    """Raised when no extracted sections are available."""


class SourceTraceabilityError(StudyGuideGenerationError):
    """Raised when the model references a source that does not exist."""


class StructuredResponseError(StudyGuideGenerationError):
    """Raised when the provider response is not valid StudyGuide JSON."""


def generate_study_guide(
    provider: LLMProvider,
    lecture_title: str,
    documents: list[Document],
    chunk_threshold: int = 40_000,
) -> StudyGuide:
    """Generate, validate, and source-check a study guide."""
    sections = [section for document in documents for section in document.sections]
    if not sections:
        raise EmptyLectureContentError(
            "The lecture has no extracted content to send for study-guide generation."
        )
    source_map = _source_map(documents)
    chunks = _chunk_documents(documents, chunk_threshold)
    try:
        if len(chunks) == 1:
            return _request_validated_guide(
                provider,
                lecture_title,
                build_source_prompt(lecture_title, chunks[0]),
                source_map,
            )
        chunk_guides = [
            _request_validated_guide(
                provider,
                lecture_title,
                build_source_prompt(lecture_title, chunk),
                source_map,
            )
            for chunk in chunks
        ]
        return _request_validated_guide(
            provider,
            lecture_title,
            build_synthesis_prompt(lecture_title, chunk_guides),
            source_map,
        )
    except AIProviderError as error:
        raise StudyGuideGenerationError(str(error)) from error


def _request_validated_guide(
    provider: LLMProvider,
    lecture_title: str,
    user_prompt: str,
    source_map: set[tuple[str, str, int]],
) -> StudyGuide:
    response = provider.generate(SYSTEM_PROMPT, user_prompt)
    try:
        return _parse_and_validate(response, lecture_title, source_map)
    except (StructuredResponseError, SourceTraceabilityError) as error:
        repaired_response = provider.generate(
            SYSTEM_PROMPT,
            build_repair_prompt(response, str(error)),
        )
        return _parse_and_validate(repaired_response, lecture_title, source_map)


def _parse_and_validate(
    response: str,
    lecture_title: str,
    source_map: set[tuple[str, str, int]],
) -> StudyGuide:
    try:
        payload = json.loads(response)
        guide = StudyGuide.model_validate(payload)
    except (json.JSONDecodeError, ValidationError, TypeError) as error:
        raise StructuredResponseError(f"The AI returned invalid study-guide JSON: {error}") from error
    if guide.lecture_title.strip() != lecture_title.strip():
        guide = guide.model_copy(update={"lecture_title": lecture_title})
    for reference in _all_references(guide):
        key = (reference.filename, reference.source_type, reference.source_index)
        if key not in source_map:
            raise SourceTraceabilityError(
                "The AI returned an invalid source reference: "
                f"{reference.filename}, {reference.source_type}, {reference.source_index}."
            )
    return guide


def _all_references(guide: StudyGuide) -> Iterable[SourceReference]:
    yield from guide.sources
    for field_name in (
        "key_concepts",
        "definitions",
        "formulas",
        "exam_topics",
        "common_confusions",
        "practice_questions",
        "knowledge_gaps",
    ):
        for item in getattr(guide, field_name):
            yield from item.source_references


def _source_map(documents: list[Document]) -> set[tuple[str, str, int]]:
    return {
        (document.filename, section.source_type, section.source_index)
        for document in documents
        for section in document.sections
    }


def _chunk_documents(
    documents: list[Document],
    chunk_threshold: int,
) -> list[list[Document]]:
    if chunk_threshold <= 0:
        raise ValueError("chunk_threshold must be greater than zero.")
    chunks: list[list[Document]] = []
    current_documents: list[Document] = []
    current_size = 0
    for document in documents:
        for section in document.sections:
            section_size = len(section.text)
            if current_documents and current_size + section_size > chunk_threshold:
                chunks.append(current_documents)
                current_documents = []
                current_size = 0
            current_documents.append(
                Document(document.filename, document.file_type, (section,))
            )
            current_size += section_size
    if current_documents:
        chunks.append(current_documents)
    return chunks
