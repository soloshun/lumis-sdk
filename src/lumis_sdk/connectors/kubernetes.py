"""Namespace-scoped Kubernetes discovery via a read-only kubectl request.

Credentials and TLS remain in the operator's kubeconfig. Discovery omits pod environment,
ConfigMaps, Secrets, annotations, and log bodies. No apply/exec/delete command exists here.
"""

import asyncio
import json
import re
from typing import Any

from lumis_sdk.core import Entity, GraphSnapshot, Relationship


def topology_from_kubernetes(payload: dict[str, Any], *, namespace: str) -> GraphSnapshot:
    """Normalize Services, Deployments and Pods, joining service selectors to pod labels.

    Service edges are declared routing matches, not proof that a runtime call happened.
    Kubernetes resource IDs are deliberately distinct from logical service identities.
    Pods that ran to completion (`Succeeded`, e.g. finished Job pods) are not current topology
    and are skipped; failed pods are kept because they may be part of the incident.
    """
    entities: dict[str, Entity] = {}
    items: dict[str, dict[str, Any]] = {}
    kinds = {"Service", "Deployment", "Pod", "ReplicaSet"}
    for item in payload.get("items", []):
        metadata = item.get("metadata", {})
        kind, name = item.get("kind"), metadata.get("name")
        if kind not in kinds or not name or metadata.get("namespace", namespace) != namespace:
            continue
        if kind == "Pod" and item.get("status", {}).get("phase") == "Succeeded":
            continue
        identity = f"k8s:{namespace}:{kind.lower()}:{name}"
        attrs = {"namespace": namespace}
        app = metadata.get("labels", {}).get("app.kubernetes.io/name")
        if app:
            attrs["service.name"] = str(app)
        entities[identity] = Entity(
            id=identity,
            kind=f"kubernetes.{kind.lower()}",
            name=name,
            attributes=attrs,
            provenance=("kubernetes",),
        )
        items[identity] = item
    edges: dict[tuple[str, str, str], Relationship] = {}
    for identity, item in items.items():
        for owner in item.get("metadata", {}).get("ownerReferences", []):
            owner_id = f"k8s:{namespace}:{str(owner.get('kind', '')).lower()}:{owner.get('name')}"
            if owner_id in entities:
                edge = Relationship(
                    source=owner_id, target=identity, kind="owns", provenance=("kubernetes",)
                )
                edges[(edge.source, edge.target, edge.kind)] = edge
        if item.get("kind") == "Service":
            selector = item.get("spec", {}).get("selector", {})
            if not selector:
                continue
            for target, pod in items.items():
                if pod.get("kind") != "Pod":
                    continue
                labels = pod.get("metadata", {}).get("labels", {})
                if all(labels.get(key) == value for key, value in selector.items()):
                    edge = Relationship(
                        source=identity,
                        target=target,
                        kind="routes_to",
                        provenance=("kubernetes.selector",),
                    )
                    edges[(edge.source, edge.target, edge.kind)] = edge
    return GraphSnapshot(
        entities=tuple(entities[key] for key in sorted(entities)),
        relationships=tuple(edges[key] for key in sorted(edges)),
    )


class KubernetesDiscovery:
    """Read only named resource kinds in one explicit namespace and context."""

    def __init__(
        self,
        *,
        namespace: str,
        context: str,
        timeout_seconds: float = 15,
        max_response_bytes: int = 2_000_000,
    ) -> None:
        if not re.fullmatch(r"[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?", namespace):
            raise ValueError("invalid Kubernetes namespace")
        if not context or context.startswith("-") or timeout_seconds <= 0 or max_response_bytes < 1:
            raise ValueError("explicit context and positive discovery bounds required")
        self.namespace = namespace
        self.context = context
        self.timeout_seconds = timeout_seconds
        self.max_response_bytes = max_response_bytes

    async def discover(self) -> GraphSnapshot:
        """Use bounded stdout and kill the child on timeout, cancellation, or overflow."""
        process = await asyncio.create_subprocess_exec(
            "kubectl",
            "--context",
            self.context,
            "--namespace",
            self.namespace,
            "get",
            "services,deployments,pods,replicasets",
            "-o",
            "json",
            f"--request-timeout={self.timeout_seconds}s",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )
        try:
            async with asyncio.timeout(self.timeout_seconds):
                assert process.stdout is not None
                try:
                    await process.stdout.readexactly(self.max_response_bytes + 1)
                except asyncio.IncompleteReadError as error:
                    data = error.partial
                else:
                    raise ValueError("Kubernetes response exceeds byte budget")
                if await process.wait():
                    raise ValueError("Kubernetes discovery unavailable")
            payload = json.loads(data)
            if not isinstance(payload, dict):
                raise ValueError("Kubernetes response must be an object")
            return topology_from_kubernetes(payload, namespace=self.namespace)
        finally:
            if process.returncode is None:
                process.kill()
                await process.wait()
