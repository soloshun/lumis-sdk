"""Regression checks for cookbook-local OpenARIA configuration layouts."""

from pathlib import Path

from openaria.config import load_config, resolve_project_path

ROOT = Path(__file__).parents[1]


def test_cookbooks_load_versioned_project_owned_rules() -> None:
    """Every cookbook keeps its scenario configuration outside framework core."""
    expected = {
        "data-pipeline-investigation": "schema_change",
        "ml-regression-monitoring": "feature_distribution_drift",
        "simple-log-diagnosis": "schema_change",
        "software-delivery-ci-investigation": "dependency_lockfile_mismatch",
    }
    configs = {
        name: load_config(ROOT / f"cookbook/{name}/openaria/openaria.yml") for name in expected
    }

    assert {name: config.rules[0].classification for name, config in configs.items()} == expected
    data_config_path = ROOT / "cookbook/data-pipeline-investigation/openaria/openaria.yml"
    data_config = configs["data-pipeline-investigation"]
    assert resolve_project_path(data_config_path, data_config.memory.path) == (
        ROOT / "cookbook/data-pipeline-investigation/.openaria/incidents.db"
    )
