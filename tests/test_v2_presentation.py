"""Focused tests for StudyGuide V2 presentation helpers."""

from app.ai.schemas import StudyGuide
from app.ui import library


REFERENCE = {
    "filename": "lecture.pdf",
    "source_type": "page",
    "source_index": 1,
}


class StreamlitRecorder:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    def expander(self, title: str, expanded: bool = False) -> "StreamlitRecorder":
        self.calls.append(("expander", title))
        return self

    def subheader(self, title: str) -> None:
        self.calls.append(("subheader", title))

    def markdown(self, value: str) -> None:
        self.calls.append(("markdown", value))

    def write(self, value: str) -> None:
        self.calls.append(("write", value))

    def caption(self, value: str) -> None:
        self.calls.append(("caption", value))

    def __enter__(self) -> "StreamlitRecorder":
        return self

    def __exit__(self, *args: object) -> None:
        return None


def _guide() -> StudyGuide:
    return StudyGuide.model_validate(
        {
            "mental_model": {
                "core_idea": "A structure organizes the operation.",
                "components": ["Input", "Operation"],
                "relationships": ["The operation transforms the input."],
                "how_it_works": "Apply the operation to the input.",
                "key_takeaway": "Choose the structure for the operation.",
            },
            "real_world_applications": [
                {
                    "title": "Search service",
                    "problem": "Users need fast lookup.",
                    "solution": "Use the covered structure.",
                    "why_this_concept": "It supports lookup.",
                    "impact": "Results arrive quickly.",
                    "source_references": [REFERENCE],
                }
            ],
            "engineering_connections": [
                {
                    "concept": "Hash table",
                    "real_world_problem": "The service needs repeated lookup.",
                    "engineering_decision": "Choose a hash table.",
                    "implementation": "Use a dictionary implementation.",
                    "trade_offs": "Memory is exchanged for speed.",
                    "source_references": [REFERENCE],
                }
            ],
        }
    )


def test_streamlit_helpers_render_v2_sections_and_references(monkeypatch) -> None:
    recorder = StreamlitRecorder()
    monkeypatch.setattr(library, "st", recorder)
    guide = _guide()

    library._render_mental_model(guide)
    library._render_real_world_applications(guide)
    library._render_engineering_connections(guide)

    values = [value for _, value in recorder.calls]
    assert "Mental Model" in values
    assert "Real-World Applications" in values
    assert "Engineering Connections" in values
    assert "A structure organizes the operation." in values
    assert "Problem: Users need fast lookup." in values
    assert "Engineering decision: Choose a hash table." in values
    assert any(value.startswith("Sources: lecture.pdf") for value in values)


def test_streamlit_helpers_skip_empty_v2_sections(monkeypatch) -> None:
    recorder = StreamlitRecorder()
    monkeypatch.setattr(library, "st", recorder)

    library._render_mental_model(StudyGuide())
    library._render_real_world_applications(StudyGuide())
    library._render_engineering_connections(StudyGuide())

    assert recorder.calls == []


def test_legacy_guide_without_v2_sections_remains_renderable(monkeypatch) -> None:
    recorder = StreamlitRecorder()
    monkeypatch.setattr(library, "st", recorder)
    legacy = StudyGuide.model_validate(
        {
            "lecture_title": "Lecture 01",
            "overview": "Legacy overview.",
            "learning_objectives": [],
            "key_concepts": [],
            "definitions": [],
            "formulas": [],
            "exam_topics": [],
            "common_confusions": [],
            "practice_questions": [],
            "quick_revision": [],
            "knowledge_gaps": [],
            "sources": [],
        }
    )

    library._render_mental_model(legacy)
    library._render_real_world_applications(legacy)
    library._render_engineering_connections(legacy)

    assert recorder.calls == []
