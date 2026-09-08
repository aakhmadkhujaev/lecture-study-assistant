"""Prompts for grounded, structured study-guide generation."""

import json

SYSTEM_PROMPT = """You are an academic study-preparation assistant.

Transform only the supplied university lecture material into a structured study guide.
Simplify difficult language while preserving technical terms, definitions, formulas,
algorithms, relationships, conditions, exceptions, examples, and distinctions.
Never invent information, use outside knowledge, perform web research, or claim that
something will be on an exam. Importance describes revision value inside the supplied
lecture, not exam prediction. If the material is insufficient, create a KnowledgeGap.
Every factual item must include valid source references. Return only JSON matching the
requested schema, with no Markdown or extra fields.

The goal is: simpler language + same knowledge + clear structure + source traceability.
"""


def build_source_prompt(lecture_title: str, documents: list[object]) -> str:
    """Build a source-marked prompt from extracted documents."""
    parts = [
        "Return a JSON object matching the StudyGuide schema.",
        f"[LECTURE TITLE]\n{lecture_title}",
        "[SOURCE MATERIAL]",
    ]
    for document in documents:
        for section in document.sections:
            parts.extend(
                [
                    "[SOURCE]",
                    f"filename={document.filename}",
                    f"source_type={section.source_type}",
                    f"source_index={section.source_index}",
                    "TEXT:",
                    section.text,
                ]
            )
    return "\n".join(parts)


def build_repair_prompt(original_response: str, error: str) -> str:
    """Ask the provider to repair only a malformed response."""
    return "\n".join(
        [
            "Repair the following response so it is valid JSON matching the StudyGuide schema.",
            "Preserve all grounded content and correct only schema or source-reference errors.",
            f"VALIDATION ERROR:\n{error}",
            f"ORIGINAL RESPONSE:\n{original_response}",
            "Return JSON only.",
        ]
    )


def build_synthesis_prompt(lecture_title: str, chunk_guides: list[object]) -> str:
    """Build a grounded synthesis request from validated chunk guides."""
    serialized = json.dumps(
        [guide.model_dump(mode="json") for guide in chunk_guides],
        ensure_ascii=False,
        indent=2,
    )
    return "\n".join(
        [
            "Return one JSON object matching the StudyGuide schema.",
            f"[LECTURE TITLE]\n{lecture_title}",
            "Synthesize only the following validated chunk guides. Preserve their source references and do not add outside knowledge.",
            "[CHUNK GUIDES]",
            serialized,
        ]
    )
