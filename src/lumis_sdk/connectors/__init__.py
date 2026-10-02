"""Read-only external integration boundaries. HTTP implementations require the 'http' extra."""

from .snapshots import SnapshotConnector, merge_topology

__all__ = ["SnapshotConnector", "merge_topology"]
