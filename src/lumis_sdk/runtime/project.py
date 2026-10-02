"""Versioned operational project configuration, separate from legacy lumis.dev/v1 rules."""

from pathlib import Path
from typing import Literal

from pydantic import Field

from lumis_sdk.config.loader import load_document_mapping
from lumis_sdk.core import EvidenceQuery, GraphSnapshot, Hypothesis, InvestigationBudget
from lumis_sdk.core.contracts import Contract, Identifier

MAX_DOCUMENT_BYTES = 2_000_000


class OperationalProject(Contract):
    """Explicit normalized topology, observation catalog, and optional provider configuration."""

    api_version: Literal["lumis.dev/operational-v1alpha1"] = "lumis.dev/operational-v1alpha1"
    name: Identifier
    graph: GraphSnapshot
    queries: tuple[EvidenceQuery, ...] = ()
    initial_query_ids: tuple[Identifier, ...] = ()
    rule_hypotheses: tuple[Hypothesis, ...] = ()
    budget: InvestigationBudget = Field(default_factory=InvestigationBudget)
    prometheus_endpoint: str | None = None
    openrouter_model: str | None = None


def load_project(path: Path) -> OperationalProject:
    """Parse bounded safe YAML with strict fields; never perform network or model calls."""
    return OperationalProject.model_validate(load_document_mapping(path))


def read_document(path: Path) -> str:
    """Bound reads even if the file grows after opening."""
    with path.open("rb") as stream:
        data = stream.read(MAX_DOCUMENT_BYTES + 1)
    if len(data) > MAX_DOCUMENT_BYTES:
        raise ValueError("operational document exceeds byte budget")
    return data.decode("utf-8")
