"""Independent CLI and YAML readiness; no consumer repository or live provider."""

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from lumis_sdk.cli.app import app
from lumis_sdk.runtime.documents import MAX_DOCUMENT_BYTES, load_mapping, read_document
from lumis_sdk.runtime.project import OperationalProject, load_project
from lumis_sdk.runtime.scaffold import starter_documents

runner = CliRunner()


def scaffold(tmp_path):
    result = runner.invoke(app, ["init", "--directory", str(tmp_path)])
    assert result.exit_code == 0, result.output
    return tmp_path / "lumis.yaml"


def test_standalone_init_doctor_discover_investigate_and_store(tmp_path):
    project = scaffold(tmp_path)
    result = runner.invoke(app, ["doctor", "--project", str(project)])
    assert json.loads(result.output) == {
        "valid": True,
        "project": "my-estate",
        "environment": "local",
        "mode": "read_only",
        "network_checked": False,
        "warnings": [],
    }
    discovered = runner.invoke(app, ["discover", "--project", str(project)])
    assert discovered.exit_code == 0, discovered.output
    topology = tmp_path / "topology.json"
    topology.write_text(discovered.output)
    args = [
        "investigate",
        "--project",
        str(project),
        "--incident",
        str(tmp_path / "incident.json"),
        "--observations",
        str(tmp_path / "observations.json"),
        "--topology",
        str(topology),
        "--store",
        str(tmp_path / "audit.sqlite"),
    ]
    investigated = runner.invoke(app, args)
    assert investigated.exit_code == 0, investigated.output
    payload = json.loads(investigated.output)
    assert payload["outcome"] == "supported"
    assert payload["truth_state"] == "unconfirmed_hypothesis"
    assert runner.invoke(app, args).exit_code != 0  # no audit overwrite
    abstained = runner.invoke(app, args[:5])
    assert abstained.exit_code == 0, abstained.output
    assert json.loads(abstained.output)["outcome"] == "abstained"


def test_init_refuses_overwrite_and_invalid_directory(tmp_path):
    project = scaffold(tmp_path)
    before = project.read_text()
    assert runner.invoke(app, ["init", "--directory", str(tmp_path)]).exit_code != 0
    assert project.read_text() == before
    bad = tmp_path / "regular-file"
    bad.write_text("untouched")
    result = runner.invoke(app, ["init", "--directory", str(bad)])
    assert result.exit_code != 0
    assert bad.read_text() == "untouched"


@pytest.mark.parametrize("command", ["diagnose", "resolve", "plugins", "rules", "config", "memory"])
def test_obsolete_commands_are_not_exposed(command):
    result = runner.invoke(app, [command])
    assert result.exit_code != 0
    assert "No such command" in result.output


@pytest.mark.parametrize(
    "patch",
    [
        {"name": "old-flat-identity"},
        {"sources": {"kubernetes": {"enabled": True}}},
        {"sources": {"prometheus": {"enabled": True}}},
        {"sources": {"prometheus": {"endpoint": "http://user:private@example.test"}}},
        {"sources": {"opentelemetry": {"enabled": True}}},
        {"sources": {"loki": {"enabled": True}}},
        {"policies": {"default_action_mode": "approval_required"}},
        {"models": {"provider": "unknown", "model": "test"}},
        {"initial_query_ids": ["unregistered"]},
    ],
)
def test_project_rejects_unimplemented_or_unsafe_configuration(patch):
    config = json.loads(starter_documents()["lumis.yaml"])
    with pytest.raises(ValueError):
        OperationalProject.model_validate(config | patch)


def test_project_rejects_duplicate_queries_and_uncovered_falsifier():
    config = json.loads(starter_documents()["lumis.yaml"])
    config["queries"] *= 2
    with pytest.raises(ValueError, match="duplicate"):
        OperationalProject.model_validate(config)
    config = json.loads(starter_documents()["lumis.yaml"])
    config["queries"].append(
        {
            "id": "other",
            "entity_id": "service:demo",
            "provider": "snapshot",
            "key": "other",
            "description": "Another registered key",
        }
    )
    config["rule_hypotheses"][0]["falsifiers"][0]["key"] = "other"
    with pytest.raises(ValueError, match="cannot be tested"):
        OperationalProject.model_validate(config)


@pytest.mark.parametrize(
    "text",
    [
        "project: {name: a}\nproject: {name: b}",
        '{"project": {"name": "a"}, "project": {"name": "b"}}',
        "project: &project {name: a}\nother: *project",
        "project: !!python/object/apply:os.system ['must-not-execute']",
    ],
)
def test_bounded_loader_rejects_ambiguous_or_unsafe_yaml(tmp_path, text):
    path = tmp_path / "lumis.yaml"
    path.write_text(text)
    with pytest.raises(ValueError):
        load_project(path)


def test_loader_rejects_size_and_depth_overflow(tmp_path):
    path = tmp_path / "large.yaml"
    path.write_text("x" * (MAX_DOCUMENT_BYTES + 1))
    with pytest.raises(ValueError, match="byte budget"):
        read_document(path)
    path.write_text("nested: " + "[" * 70 + "0" + "]" * 70)
    with pytest.raises(ValueError, match="depth budget"):
        load_mapping(path)


def test_otlp_discovery_uses_project_relative_export_and_no_private_payload(tmp_path):
    project = scaffold(tmp_path)
    config = json.loads(project.read_text())
    config["sources"] = {"opentelemetry": {"enabled": True, "export_file": "traces.json"}}
    project.write_text(json.dumps(config))
    (tmp_path / "traces.json").write_text(
        json.dumps(
            {
                "resourceSpans": [
                    {
                        "resource": {
                            "attributes": [
                                {
                                    "key": "service.name",
                                    "value": {"stringValue": "external-service"},
                                },
                                {"key": "private", "value": {"stringValue": "must-not-export"}},
                            ]
                        },
                        "scopeSpans": [],
                    }
                ]
            }
        )
    )
    result = runner.invoke(app, ["discover", "--project", str(project)])
    assert result.exit_code == 0, result.output
    assert "external-service" in result.output
    assert "must-not-export" not in result.output


def test_doctor_reports_missing_key_without_network_or_secret(tmp_path, monkeypatch):
    project = scaffold(tmp_path)
    config = json.loads(project.read_text())
    config["models"] = {
        "provider": "anthropic",
        "model": "test-model",
        "api_key_env": "LUMIS_TEST_KEY",
    }
    project.write_text(json.dumps(config))
    monkeypatch.delenv("LUMIS_TEST_KEY", raising=False)
    result = runner.invoke(app, ["doctor", "--project", str(project)])
    payload = json.loads(result.output)
    assert payload["network_checked"] is False
    assert len(payload["warnings"]) == 1
    assert "LUMIS_TEST_KEY" not in result.output


def test_documents_have_no_broken_local_markdown_links():
    import re

    root = Path(__file__).parents[1]
    for path in [*root.glob("*.md"), *root.glob("docs/*.md")]:
        for link in re.findall(r"\]\(([^)]+)\)", path.read_text()):
            if "://" not in link and not link.startswith("#"):
                assert (path.parent / link.split("#")[0]).exists(), (path, link)
