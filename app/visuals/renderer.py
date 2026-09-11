"""Deterministic presentation of validated visual mental models."""

from app.ai.schemas import VisualModel
from app.pdf.styles import BODY_STYLE, SUBSECTION_STYLE
from app.pdf.utils import add_reference, paragraph


def render_visual_text(visual: VisualModel) -> str:
    """Return a readable, deterministic text diagram."""
    labels = {node.id: node.label for node in visual.nodes}
    if not labels:
        return "(No nodes)"
    if visual.diagram_type in {"flow", "process"}:
        return _render_sequence(visual, labels)
    if visual.diagram_type == "hierarchy":
        return _render_hierarchy(visual, labels)
    if visual.diagram_type == "comparison":
        return _render_comparison(visual, labels)
    return _render_relationships(visual, labels)


def render_visual_flowables(visual: VisualModel) -> list[object]:
    """Return ReportLab flowables for one visual model."""
    story: list[object] = [
        paragraph(visual.title, SUBSECTION_STYLE),
        paragraph(f"Purpose: {visual.purpose}"),
        paragraph(render_visual_text(visual), BODY_STYLE),
        paragraph(visual.explanation),
    ]
    add_reference(story, visual.source_references)
    return story


def _render_sequence(visual: VisualModel, labels: dict[str, str]) -> str:
    ordered = [labels[node.id] for node in visual.nodes]
    return " → ".join(ordered)


def _render_hierarchy(visual: VisualModel, labels: dict[str, str]) -> str:
    children: dict[str, list[tuple[str, str | None]]] = {node_id: [] for node_id in labels}
    targets: set[str] = set()
    for relationship in visual.relationships:
        children[relationship.source].append(
            (relationship.target, relationship.label)
        )
        targets.add(relationship.target)
    roots = [node_id for node_id in labels if node_id not in targets]
    lines: list[str] = []
    visited: set[str] = set()

    def visit(node_id: str, prefix: str) -> None:
        if node_id in visited:
            return
        visited.add(node_id)
        lines.append(f"{prefix}{labels[node_id]}")
        for index, (child_id, relation_label) in enumerate(children[node_id]):
            branch = "└── " if index == len(children[node_id]) - 1 else "├── "
            label = f"{relation_label} → " if relation_label else ""
            visit(child_id, prefix + branch + label)

    for root in roots or list(labels):
        visit(root, "")
    for node_id in labels:
        visit(node_id, "")
    return "\n".join(lines)


def _render_comparison(visual: VisualModel, labels: dict[str, str]) -> str:
    columns = "    ".join(labels[node.id] for node in visual.nodes)
    relationships = "\n".join(
        f"{labels.get(item.source, item.source)}: {item.label or 'related to'} "
        f"{labels.get(item.target, item.target)}"
        for item in visual.relationships
    )
    return f"{columns}\n{'─' * max(len(columns), 1)}\n{relationships or 'Compare the concepts above.'}"


def _render_relationships(visual: VisualModel, labels: dict[str, str]) -> str:
    lines = [labels[node.id] for node in visual.nodes]
    for relationship in visual.relationships:
        label = f" {relationship.label} " if relationship.label else " → "
        lines.append(
            f"{labels.get(relationship.source, relationship.source)}"
            f"{label}"
            f"{labels.get(relationship.target, relationship.target)}"
        )
    return "\n".join(lines)
