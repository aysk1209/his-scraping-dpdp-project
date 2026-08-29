"""The five-layer architecture and its interoperability mapping stay consistent."""

from interop.layers import HISLayer, LAYER_DESCRIPTIONS
from interop.mapping import LAYER_STANDARDS, InteropStandard, standards_for


def test_exactly_five_layers() -> None:
    assert len(list(HISLayer)) == 5


def test_every_layer_has_a_description() -> None:
    assert set(LAYER_DESCRIPTIONS) == set(HISLayer)


def test_every_layer_is_mapped() -> None:
    assert set(LAYER_STANDARDS) == set(HISLayer)


def test_hl7_and_fhir_cover_the_clinical_layers() -> None:
    for layer in (HISLayer.PATIENT_ADMINISTRATION, HISLayer.CLINICAL_EHR):
        stds = standards_for(layer)
        assert InteropStandard.HL7_V2 in stds
        assert InteropStandard.FHIR in stds


def test_infrastructure_layer_carries_no_record_standard() -> None:
    assert standards_for(HISLayer.INFRASTRUCTURE_INTEGRATION) == ()
