"""Synthetic read-only inspection target; no connections or side effects."""


def load_features(item_ids, store):
    """Illustrative per-item access; the notebook does not execute this function."""
    return [store.fetch_one(item_id) for item_id in item_ids]
