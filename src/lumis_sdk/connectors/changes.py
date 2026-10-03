"""Typed recent-change records: what changed, where in the graph, and when.

A change is a time-bounded fact about an entity, not a graph node: the graph stays the estate's
current structure, and changes reach diagnosis as evidence (`provider: changes`) and through the
agent's `inspect(changes)` tool. Backends are read-only: `git log` on operator-mapped paths and
Kubernetes ReplicaSet history plus `ScalingReplicaSet` events.
"""

import json
import os
import re
from collections.abc import Awaitable, Callable, Mapping, Sequence
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Literal

from pydantic import AwareDatetime, Field

from lumis_sdk.connectors.settings import ChangeQuery, ChangeSource, GitChangeSource
from lumis_sdk.core import Evidence, EvidenceQuery, Incident
from lumis_sdk.core.contracts import Contract, Identifier, Text
from lumis_sdk.investigation.process import ProcessOutput, run_bounded
from lumis_sdk.security.redaction import redact_text

MAX_OUTPUT_BYTES = 2_000_000
_SCOPE = re.compile(r"^[A-Za-z]+\(([^)]+)\)!?:")
_ACTIVATED = re.compile(r"^Scaled up replica set (\S+) from 0 to \d+$")
Runner = Callable[..., Awaitable[ProcessOutput]]


class ChangeRecord(Contract):
    id: Identifier
    kind: Literal["commit", "rollout"]
    source: Identifier
    at: AwareDatetime
    entity_ids: tuple[Identifier, ...] = Field(min_length=1, max_length=100)
    summary: Text
    reference: Identifier


def _timestamp(value: str) -> datetime:
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.tzinfo is None:
        raise ValueError("change timestamp requires a timezone")
    return result


def commits_from_git_log(
    text: str, source: GitChangeSource, aliases: Mapping[str, str]
) -> tuple[ChangeRecord, ...]:
    """Parse `--format=%x1e%H%x1f%cI%x1f%s --name-only` output into records for mapped paths.

    Entities come from the changed paths; a recognised conventional-commit scope narrows them
    (a shared kustomization.yaml maps to every service, `deploy(feature-service): ...` to one).
    """
    records = []
    for block in text.split("\x1e"):
        if not block.strip():
            continue
        header, _, names = block.partition("\n")
        sha, committed, subject = header.split("\x1f", 2)
        if len(sha) != 40 or any(char not in "0123456789abcdef" for char in sha):
            raise ValueError("unexpected Git metadata format")
        changed = [name for name in names.splitlines() if name]
        by_path = {
            entity
            for path, mapped in source.paths.items()
            for name in changed
            if name == path or name.startswith(path.rstrip("/") + "/")
            for entity in mapped
        }
        scope = _SCOPE.match(subject)
        by_scope = {
            entity
            for name in (scope.group(1).split(",") if scope else ())
            for entity in source.scopes.get(name.strip(), ())
        }
        entities = sorted(
            {aliases.get(entity, entity) for entity in (by_path & by_scope) or by_path}
        )
        if not entities:
            continue
        files = ", ".join(changed[:5]) + (
            f" (+{len(changed) - 5} more)" if len(changed) > 5 else ""
        )
        records.append(
            ChangeRecord(
                id=f"git:{source.id}:{sha}",
                kind="commit",
                source=source.id,
                at=_timestamp(committed),
                entity_ids=tuple(entities),
                summary=redact_text(f"{subject[:200]} [{files}]")[:1000],
                reference=sha,
            )
        )
    return tuple(records)


def rollouts_from_kubernetes(
    payload: dict[str, Any],
    *,
    namespace: str,
    aliases: Mapping[str, str],
    events: dict[str, Any] | None = None,
) -> tuple[ChangeRecord, ...]:
    """Rollouts from Deployment-owned ReplicaSets.

    A new ReplicaSet's creation is a rollout. Re-activating an existing ReplicaSet (a rollback,
    or a GitOps revert-and-reapply) keeps its old creation time; Kubernetes records it only as a
    `ScalingReplicaSet` event ("Scaled up replica set X from 0 to N"), and events expire (one hour
    by default). Those events add re-activation records while they last; a Git source is the
    durable record.
    """
    activations: dict[str, list[datetime]] = {}
    for event in (events or {}).get("items", []):
        match = _ACTIVATED.match(str(event.get("message", "")))
        when = event.get("lastTimestamp") or event.get("eventTime")
        if event.get("reason") == "ScalingReplicaSet" and match and when:
            activations.setdefault(match.group(1), []).append(_timestamp(str(when)))
    revisions: dict[str, list[tuple[int, dict[str, Any]]]] = {}
    for item in payload.get("items", []):
        if item.get("kind", "ReplicaSet") != "ReplicaSet":
            continue
        owner = next(
            (
                ref.get("name")
                for ref in item.get("metadata", {}).get("ownerReferences", [])
                if ref.get("kind") == "Deployment"
            ),
            None,
        )
        revision = (
            item.get("metadata", {}).get("annotations", {}).get("deployment.kubernetes.io/revision")
        )
        if owner and revision and str(revision).isdigit():
            revisions.setdefault(owner, []).append((int(revision), item))
    records: list[ChangeRecord] = []
    for owner, items in revisions.items():
        items.sort(key=lambda pair: pair[0])
        previous_images: list[str] = []
        for revision, item in items:
            metadata = item.get("metadata", {})
            name = str(metadata.get("name"))
            template = item.get("spec", {}).get("template", {})
            images = [
                str(container.get("image", ""))
                for container in template.get("spec", {}).get("containers", [])
            ]
            labels = template.get("metadata", {}).get("labels", {}) or metadata.get("labels", {})
            entities = {f"k8s:{namespace}:deployment:{owner}"}
            if app := labels.get("app.kubernetes.io/name"):
                entities.add(f"service:{namespace}:{app}")
            entity_ids = tuple(sorted(aliases.get(entity, entity) for entity in entities))
            change = (
                f"images {', '.join(previous_images)} -> {', '.join(images)}"
                if previous_images and previous_images != images
                else f"images {', '.join(images)}"
            )
            created = _timestamp(str(metadata.get("creationTimestamp")))
            records.append(
                ChangeRecord(
                    id=f"k8s:{namespace}:rollout:{name}",
                    kind="rollout",
                    source="kubernetes",
                    at=created,
                    entity_ids=entity_ids,
                    summary=redact_text(f"deployment {owner} revision {revision}: {change}")[:1000],
                    reference=name,
                )
            )
            for activated in activations.get(name, ()):
                if activated - created > timedelta(minutes=2):  # not the creation itself
                    summary = f"deployment {owner} re-activated {name}: images {', '.join(images)}"
                    records.append(
                        ChangeRecord(
                            id=f"k8s:{namespace}:rollout:{name}:{int(activated.timestamp())}",
                            kind="rollout",
                            source="kubernetes",
                            at=activated,
                            entity_ids=entity_ids,
                            summary=redact_text(summary)[:1000],
                            reference=name,
                        )
                    )
            previous_images = images
    return tuple(records)


class ChangeConnector:
    """Read-only change history, cached per (window end, lookback) for one investigation."""

    def __init__(
        self,
        source: ChangeSource,
        *,
        base: Path,
        kubernetes: tuple[str, str] | None = None,
        aliases: Mapping[str, str] | None = None,
        runner: Runner = run_bounded,
        timeout_seconds: float = 10,
    ) -> None:
        if not source.enabled:
            raise ValueError("enabled change source required")
        if source.kubernetes_rollouts and kubernetes is None:
            raise ValueError("Kubernetes rollouts require the Kubernetes source context/namespace")
        self.source, self.base, self.kubernetes = source, base, kubernetes
        self.aliases = dict(aliases or {})
        self.runner, self.timeout = runner, timeout_seconds
        self._cache: dict[tuple[datetime, int], tuple[ChangeRecord, ...]] = {}

    async def _git(self, source: GitChangeSource, since: datetime, until: datetime) -> str:
        raw = Path(source.root)
        root = raw if raw.is_absolute() else self.base / raw
        command: Sequence[str] = [
            "git",
            "--no-pager",
            "--no-optional-locks",
            "--literal-pathspecs",
            "-C",
            str(root),
            "-c",
            "core.fsmonitor=false",
            "-c",
            "core.hooksPath=/dev/null",
            "log",
            "--max-count=200",
            "--no-renames",
            "--name-only",
            "--format=%x1e%H%x1f%cI%x1f%s",
            f"--since={since.isoformat()}",
            f"--until={until.isoformat()}",
            "--",
            *source.paths,
        ]
        result = await self.runner(
            command,
            timeout=self.timeout,
            max_bytes=MAX_OUTPUT_BYTES,
            env={
                "PATH": os.defpath,
                "GIT_CONFIG_NOSYSTEM": "1",
                "GIT_CONFIG_GLOBAL": "/dev/null",
                "GIT_TERMINAL_PROMPT": "0",
            },
        )
        if result.exit_code:
            raise ValueError("Git change history unavailable")
        return result.stdout.decode("utf-8")

    async def _kubectl(self, *resource: str) -> dict[str, Any]:
        assert self.kubernetes is not None
        context, namespace = self.kubernetes
        result = await self.runner(
            ["kubectl", "--context", context, "--namespace", namespace, "get", *resource]
            + ["-o", "json", f"--request-timeout={self.timeout}s"],
            timeout=self.timeout,
            max_bytes=MAX_OUTPUT_BYTES,
        )
        if result.exit_code:
            raise ValueError("Kubernetes rollout history unavailable")
        payload = json.loads(result.stdout)
        if not isinstance(payload, dict):
            raise ValueError("Kubernetes response must be an object")
        return payload

    async def history(
        self, *, until: datetime, lookback_seconds: int | None = None
    ) -> tuple[ChangeRecord, ...]:
        """All changes in (until - lookback, until], newest first. Any unreadable backend makes the
        history unavailable rather than silently partial."""
        lookback = lookback_seconds or self.source.lookback_seconds
        key = (until, lookback)
        if key not in self._cache:
            since = until - timedelta(seconds=lookback)
            records: list[ChangeRecord] = []
            for repository in self.source.git:
                text = await self._git(repository, since, until)
                records += commits_from_git_log(text, repository, self.aliases)
            if self.source.kubernetes_rollouts:
                assert self.kubernetes is not None
                records += rollouts_from_kubernetes(
                    await self._kubectl("replicasets"),
                    namespace=self.kubernetes[1],
                    aliases=self.aliases,
                    events=await self._kubectl(
                        "events", "--field-selector", "reason=ScalingReplicaSet"
                    ),
                )
            in_window = [record for record in records if since < record.at <= until]
            self._cache[key] = tuple(sorted(in_window, key=lambda r: (r.at, r.id), reverse=True))
        return self._cache[key]

    async def records(
        self,
        *,
        until: datetime,
        entity_ids: Sequence[str] | None = None,
        lookback_seconds: int | None = None,
        kinds: Sequence[str] = (),
    ) -> tuple[tuple[ChangeRecord, ...], bool]:
        """Matching records (bounded by max_records) and whether the bound truncated them."""
        selected = [
            record
            for record in await self.history(until=until, lookback_seconds=lookback_seconds)
            if (entity_ids is None or set(record.entity_ids) & set(entity_ids))
            and (not kinds or record.kind in kinds)
        ]
        return tuple(selected[: self.source.max_records]), len(selected) > self.source.max_records

    async def collect(self, query: EvidenceQuery, incident: Incident) -> tuple[Evidence, ...]:
        parameters = ChangeQuery.model_validate(query.parameters)
        found, truncated = await self.records(
            until=incident.ended_at,
            entity_ids=(query.entity_id,),
            lookback_seconds=parameters.lookback_seconds,
            kinds=() if parameters.kind == "any" else (parameters.kind,),
        )
        if parameters.output == "count":
            value: int | float = len(found)  # authoritative history: zero is an observation
        elif found:
            value = round((incident.ended_at - found[0].at).total_seconds(), 3)
        else:
            return ()  # no change in the lookback: "time since latest" is unknown, not zero
        return (
            Evidence(
                id=f"changes:{query.id}",
                query_id=query.id,
                entity_id=query.entity_id,
                key=query.key,
                value=value,
                # Counted over the lookback ending at the incident end.
                observed_at=incident.ended_at,
                source="changes",
                retrieval_method="git log on mapped paths / Kubernetes ReplicaSet history",
                quality="degraded" if truncated else "observed",
            ),
        )
