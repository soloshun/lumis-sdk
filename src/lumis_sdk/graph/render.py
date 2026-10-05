"""Small deterministic SVG/terminal renderers; the operational graph still drives reasoning."""

import html
import math

from lumis_sdk.core import GraphSnapshot
from lumis_sdk.security.redaction import redact_text


def svg(snapshot: GraphSnapshot) -> str:
    if len(snapshot.entities) > 200 or len(snapshot.relationships) > 1000:
        raise ValueError("visualization too large; select a smaller incident neighborhood")
    lines = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="750" viewBox="0 0 1000 750">',
        "<title>Lumis operational graph — observed/declared relations, not causal proof</title>",
        '<defs><marker id="arrow" markerWidth="10" markerHeight="10" refX="9" refY="3" '
        'orient="auto"><path d="M0,0 L0,6 L9,3 z" fill="#64748b"/></marker></defs>',
        '<rect width="1000" height="750" fill="#f8fafc"/>',
    ]
    # Drawing also works in core-only wheels without NumPy or Graphviz.
    coordinates = {
        entity.id: (
            500 + 380 * math.cos(2 * math.pi * index / len(snapshot.entities)),
            375 + 260 * math.sin(2 * math.pi * index / len(snapshot.entities)),
        )
        for index, entity in enumerate(sorted(snapshot.entities, key=lambda item: item.id))
    }
    if len(snapshot.entities) == 1:
        coordinates[snapshot.entities[0].id] = (500, 375)
    for edge in snapshot.relationships:
        x1, y1 = coordinates[edge.source]
        x2, y2 = coordinates[edge.target]
        label = html.escape(redact_text(edge.kind))
        lines += [
            f'<line x1="{x1:.2f}" y1="{y1:.2f}" x2="{x2:.2f}" y2="{y2:.2f}" '
            'stroke="#64748b" marker-end="url(#arrow)"/>',
            f'<text x="{(x1 + x2) / 2:.2f}" y="{(y1 + y2) / 2 - 8:.2f}" font-family="sans-serif" '
            f'font-size="11" fill="#334155">{label}</text>',
        ]
    for entity in snapshot.entities:
        x, y = coordinates[entity.id]
        label = html.escape(redact_text(entity.name[:48]))
        identity = html.escape(entity.id)
        lines += [
            f'<g><title>{identity}</title><circle cx="{x:.2f}" cy="{y:.2f}" '
            'r="12" fill="#2563eb"/>',
            f'<text x="{x:.2f}" y="{y + 28:.2f}" text-anchor="middle" font-family="sans-serif" '
            f'font-size="13" fill="#0f172a">{label}</text></g>',
        ]
    return "\n".join([*lines, "</svg>"])


def terminal(snapshot: GraphSnapshot) -> str:
    if len(snapshot.entities) > 100 or len(snapshot.relationships) > 200:
        raise ValueError("terminal graph too large; select an incident neighborhood")
    lines = ["LUMIS / operational graph", ""]
    lines += [f"  [{entity.id}] {redact_text(entity.name)}" for entity in snapshot.entities]
    lines += [
        "",
        *[f"  {edge.source} --{edge.kind}--> {edge.target}" for edge in snapshot.relationships],
    ]
    if not snapshot.relationships:
        lines.append("  (no relationships in this snapshot)")
    return "\n".join(lines)
