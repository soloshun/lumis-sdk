"""Regression checks for cookbook-local OpenARIA configuration layouts."""

from pathlib import Path

from openaria.config import load_config, resolve_project_path

ROOT = Path(__file__).parents[1]


def test_data_and_ml_cookbooks_load_project_owned_rules() -> None:
    """Agentic cookbooks keep reusable configuration below their openaria directory."""
    data_config_path = ROOT / "cookbook/data-pipeline-investigation/openaria/openaria.yml"
    ml_config_path = ROOT / "cookbook/ml-regression-monitoring/openaria/openaria.yml"

    data_config = load_config(data_config_path)
    ml_config = load_config(ml_config_path)

    assert data_config.rules[0].classification == "schema_change"
    assert ml_config.rules[0].classification == "feature_distribution_drift"
    assert resolve_project_path(data_config_path, data_config.memory.path) == (
        ROOT / "cookbook/data-pipeline-investigation/.openaria/incidents.db"
    )
