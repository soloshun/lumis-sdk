"""Bounded, alias-free YAML/JSON loading for untrusted local configuration."""

import json
from pathlib import Path
from typing import Any

import yaml
from yaml.events import AliasEvent
from yaml.nodes import MappingNode, Node

MAX_DOCUMENT_BYTES = 1_048_576
MAX_DOCUMENT_DEPTH = 64


class BoundedSafeLoader(yaml.SafeLoader):
    """Reject aliases, duplicate keys and excessive nesting; never construct Python objects."""

    def __init__(self, stream: str) -> None:
        super().__init__(stream)
        self.depth = 0

    def compose_node(self, parent: Node | None, index: int) -> Node:
        if self.check_event(AliasEvent):  # type: ignore[no-untyped-call]
            raise ValueError("YAML aliases are not supported")
        self.depth += 1
        if self.depth > MAX_DOCUMENT_DEPTH:
            raise ValueError("YAML nesting exceeds depth budget")
        try:
            node = super().compose_node(parent, index)
            if node is None:
                raise ValueError("empty YAML node")
            return node
        finally:
            self.depth -= 1

    def construct_mapping(self, node: MappingNode, deep: bool = False) -> dict[Any, Any]:
        keys = [self.construct_object(key, deep=deep) for key, _ in node.value]
        if len(set(keys)) != len(keys):
            raise ValueError("duplicate YAML mapping keys")
        return super().construct_mapping(node, deep=deep)


def read_document(path: Path) -> str:
    """Bound the actual read, not merely a potentially stale stat result."""
    with path.open("rb") as stream:
        data = stream.read(MAX_DOCUMENT_BYTES + 1)
    if len(data) > MAX_DOCUMENT_BYTES:
        raise ValueError("document exceeds byte budget")
    return data.decode("utf-8")


def load_mapping(path: Path) -> dict[str, Any]:
    """Load a mapping with one safe parser for JSON (a YAML subset) and YAML."""
    try:
        # SafeLoader subclass enforces local limits; no arbitrary-object constructors.
        raw = yaml.load(read_document(path), Loader=BoundedSafeLoader)  # nosec B506
    except (RecursionError, yaml.YAMLError) as error:
        raise ValueError("invalid or excessively nested document") from error
    if not isinstance(raw, dict) or any(not isinstance(key, str) for key in raw):
        raise ValueError("document root must be a string-keyed mapping")
    return raw


def json_document(value: Any) -> str:
    """Stable readable serialization for scaffold and diagnostic output."""
    return json.dumps(value, indent=2, sort_keys=True) + "\n"
