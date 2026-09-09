"""Prompts for grounded, structured study-guide generation."""

import json

SYSTEM_PROMPT = """You are an academic study-preparation assistant.

Transform only the supplied university lecture material into a concise, exam-oriented
study guide. The source material is the complete authority: do not use outside
knowledge, web research, or unstated assumptions. Never invent facts, examples,
definitions, formulas, algorithm steps, exam predictions, or missing explanations.
Preserve the lecture's technical terminology, notation, relationships, conditions,
exceptions, examples, and distinctions. Simplify wording only when the meaning stays
the same.

Populate a section when the lecture supports it and leave it as an empty list when it
does not. Do not add generic filler to make sections look complete. Every generated
item that has source_references in the schema must cite the source marker(s) that
 support it. The sources list must contain only the deduplicated source locations
 actually used by generated items. Do not list every supplied slide or page merely
 because it was available, and do not omit a used location because another optional
 section is empty.

Section rules:
- definitions: extract a term only when the lecture defines it, explicitly describes
    what it is, or gives a clear defining characterization. Preserve the lecture's
    definition rather than substituting a textbook definition.
- formulas and algorithms: include only formulas, complexity expressions, or named
    algorithm procedures actually present in the lecture. Preserve exact notation and
    stated steps. Do not turn an illustrative example into a general rule.
- common confusions: include only a contrast or misconception supported by the lecture.
- practice_questions: create a small set (usually 2-6) from explicitly covered
    material only. Prefer definition, explanation, comparison, complexity, and supported
    application questions. Use the existing schema type formula_interpretation for a
    complexity or formula question when appropriate. Model answers must be answerable
    from the lecture.
- knowledge_gaps: use only when the lecture mentions a meaningful topic but does not
    explain enough to understand or apply it. Cite the mention that demonstrates the
    gap. Do not treat an unmentioned topic as a gap.
- exam_topics: use Must Know for foundational concepts explicitly emphasized or needed
    to understand later lecture material, Important for useful supporting concepts, and
    Supporting for secondary or contextual material. Never say a topic will be on the
    exam unless the lecture explicitly says so.

Big O must remain precise. Use the lecture's actual explanation of growth with input
    size and its stated examples. Define each complexity class in terms of how the
    number of operations or running time scales as input size changes, using only the
    level of precision supported by the lecture. Do not define O(log n) as merely
    "shrinking the problem each step." If binary search is used, it may illustrate why
    an algorithm has logarithmic complexity, while the complexity definition must still
    describe scaling with input size. Preserve any stated precondition such as a sorted
    list, and do not add mathematical claims not supported by the source.

Return only JSON matching the requested schema, with no Markdown or extra fields.
"""


def build_source_prompt(lecture_title: str, documents: list[object]) -> str:
    """Build a source-marked prompt from extracted documents."""
    parts = [
        "Return a JSON object matching the StudyGuide schema.",
        f"[LECTURE TITLE]\n{lecture_title}",
        "Apply all section rules in the system instruction. Extract supported content, but leave unsupported optional lists empty.",
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
            "Synthesize only the following validated chunk guides. Preserve their source references and do not add outside knowledge or filler. Keep optional sections empty when the chunk guides provide no grounded support.",
            "[CHUNK GUIDES]",
            serialized,
        ]
    )
