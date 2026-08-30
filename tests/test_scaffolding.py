"""Build step 1: every scaffolded module imports cleanly."""

import importlib

import pytest

MODULES = [
    "compliance",
    "compliance.rules",
    "compliance.rules.minimisation",
    "compliance.rules.lawful_basis",
    "compliance.rules.storage",
    "compliance.rules.security",
    "compliance.rules.purpose_limitation",
    "compliance.rules.notice",
    "compliance.rules.accountability",
    "compliance.checkers",
    "compliance.summary",
    "compliance.benchmark",
    "data_synthetic",
    "data_synthetic.schemas",
    "data_synthetic.generators",
    "extraction",
    "extraction.base",
    "extraction.technique",
    "extraction.techniques",
    "extraction.techniques.compliant",
    "extraction.techniques.minimising",
    "extraction.techniques.unconstrained",
    "extraction.adapters",
    "extraction.adapters.mock_his",
    "extraction.adapters.live_his",
    "extraction.tier2",
    "agent",
    "interop",
    "interop.layers",
    "interop.mapping",
    "interop.hl7.messages",
    "interop.fhir.resources",
    "interop.dicom.metadata",
    "interop.iso_ieee_11073.pocd",
]


@pytest.mark.parametrize("name", MODULES)
def test_module_imports(name: str) -> None:
    importlib.import_module(name)


def test_live_his_adapter_refuses_construction() -> None:
    """The live adapter must exist but stay unusable until data access (step 7)."""
    from extraction.adapters.live_his import LiveHISDataSource

    with pytest.raises(NotImplementedError):
        LiveHISDataSource()
