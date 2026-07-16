"""Reusable test doubles for Lumis SDK integrations."""

from .contracts import assert_evidence_collection_contract, assert_json_report_round_trip
from .fakes import FakeEvidenceProvider, FakeModelGateway
from .fixtures import make_test_collection_fields, make_test_evidence, make_test_incident
from .plugins import FakePluginFactory, assert_plugin_factory_contract, make_test_plugin_manifest

__all__ = [
    "FakeEvidenceProvider",
    "FakeModelGateway",
    "FakePluginFactory",
    "assert_evidence_collection_contract",
    "assert_json_report_round_trip",
    "assert_plugin_factory_contract",
    "make_test_evidence",
    "make_test_collection_fields",
    "make_test_incident",
    "make_test_plugin_manifest",
]
