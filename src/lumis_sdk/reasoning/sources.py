"""Rules, memory, and models propose the same falsifiable type through the same port."""

from dataclasses import dataclass
from typing import Protocol

from lumis_sdk.core import Hypothesis, IncidentContext


class HypothesisSource(Protocol):
    """A candidate source, with no tools or execution authority."""

    @property
    def name(self) -> str:
        """Stable source provenance label."""
        ...

    async def propose(self, context: IncidentContext) -> tuple[Hypothesis, ...]:
        """Return candidates; the registry independently validates every one."""
        ...


class HypothesisModel(Protocol):
    """Provider-neutral structured model boundary."""

    async def generate(self, context: IncidentContext) -> tuple[Hypothesis, ...]:
        """Return schema-validated candidates, never conclusions."""
        ...


@dataclass(frozen=True)
class RuleSource:
    """Explicit reusable candidates; applicability is checked by the registry and observations."""

    candidates: tuple[Hypothesis, ...]
    name: str = "rules"

    async def propose(self, context: IncidentContext) -> tuple[Hypothesis, ...]:
        return self.candidates


@dataclass(frozen=True)
class MemoryHypothesisSource:
    """Retrieved precedents are re-tested, including previously supported candidates.

    Retrieval/ranking and environment isolation belong to the caller's memory adapter. The
    candidate set cannot carry a prior episode's supporting evidence into a new incident.
    """

    candidates: tuple[Hypothesis, ...]
    name: str = "memory"

    async def propose(self, context: IncidentContext) -> tuple[Hypothesis, ...]:
        return self.candidates


@dataclass(frozen=True)
class ModelHypothesisSource:
    """Swap any structured model provider without changing the evaluation path."""

    model: HypothesisModel
    name: str = "model"

    async def propose(self, context: IncidentContext) -> tuple[Hypothesis, ...]:
        return await self.model.generate(context)
