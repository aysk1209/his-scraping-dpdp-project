"""Tests for HL7 v2 / FHIR shaping, pseudonymisation on export, and the export audit."""

from __future__ import annotations

import json

from compliance.models import Purpose
from compliance.pseudonymise import is_token, pseudonymise_row, token_for
from extraction.adapters.mock_his import MockHISDataSource
from extraction.technique import ExtractionTask, LayerFields
from extraction.techniques import DEFAULT_TECHNIQUES
from extraction.techniques.compliant import CompliantExtractionTechnique
from extraction.techniques.unconstrained import UnconstrainedExtractionTechnique
from interop.fhir.resources import shape_fhir
from interop.hl7.messages import Message, Segment, shape_hl7
from interop.layers import HISLayer
from interop.normalise import audit, normalise

PA = HISLayer.PATIENT_ADMINISTRATION
EHR = HISLayer.CLINICAL_EHR
FIN = HISLayer.ADMINISTRATIVE_FINANCIAL

ROW = {"mrn": "MRN1234567", "full_name": "Priya Raman", "date_of_birth": "1988-03-14",
       "sex": "F", "phone": "+91-9800000012", "admission_ward": "Ward B"}

TASK = ExtractionTask(
    task_id="t", purpose=Purpose.CARE_COORDINATION,
    needed=[LayerFields(layer=PA, fields=["mrn", "full_name", "sex"]),
            LayerFields(layer=EHR, fields=["primary_diagnosis", "medication"])],
)


# --- HL7 v2 --------------------------------------------------------------------

def test_segment_fields_land_at_their_hl7_positions():
    seg = Segment("PV1").set(1, "1").set(3, "Ward B").set(44, "20260912")
    encoded = seg.encode()
    fields = encoded.split("|")
    assert fields[0] == "PV1" and fields[1] == "1" and fields[3] == "Ward B" and fields[44] == "20260912"


def test_message_starts_with_a_well_formed_msh():
    msg = Message("ADT^A04", "ctrl-1")
    msh = msg.encode().split("\r")[0].split("|")
    assert msh[0] == "MSH" and msh[1] == "^~\\&"
    assert msh[8] == "ADT^A04" and msh[9] == "ctrl-1" and msh[11] == "2.5"


def test_adt_carries_only_the_fields_that_were_extracted():
    msg = shape_hl7(PA, {"mrn": "MRN1", "sex": "M"}, "c")
    pid = next(s for s in msg.segments if s.name == "PID").encode().split("|")
    assert pid[3].startswith("MRN1") and pid[8] == "M"
    assert len(pid) <= 9                      # nothing set past PID-8
    assert "PV1" not in msg.segment_names()   # no ward, no admission -> no PV1
    assert "EVN" not in msg.segment_names()


def test_every_layer_with_an_hl7_type_gets_a_message():
    assert shape_hl7(PA, ROW, "c").message_type == "ADT^A04"
    assert shape_hl7(EHR, {"primary_diagnosis": "x", "medication": "y"}, "c").message_type == "ORM^O01"
    assert shape_hl7(HISLayer.ANCILLARY_DEPARTMENTAL, {"result_value": 1.0}, "c").message_type == "ORU^R01"
    assert shape_hl7(FIN, {"invoice_id": "INV1"}, "c").message_type == "DFT^P03"
    assert shape_hl7(HISLayer.INFRASTRUCTURE_INTEGRATION, ROW, "c") is None


# --- FHIR --------------------------------------------------------------------

def test_patient_resource_has_only_extracted_elements():
    (patient,) = shape_fhir(PA, {"mrn": "MRN1", "sex": "F"})
    assert patient["resourceType"] == "Patient"
    assert patient["identifier"][0]["value"] == "MRN1"
    assert patient["gender"] == "female"
    assert "name" not in patient and "telecom" not in patient and "birthDate" not in patient


def test_encounter_only_when_the_visit_was_extracted():
    assert [r["resourceType"] for r in shape_fhir(PA, {"mrn": "MRN1"})] == ["Patient"]
    types = [r["resourceType"] for r in shape_fhir(PA, ROW)]
    assert types == ["Patient", "Encounter"]


def test_clinical_row_yields_one_resource_per_clinical_element():
    types = {r["resourceType"] for r in shape_fhir(EHR, {
        "primary_diagnosis": "x", "medication": "y", "allergy": "z", "lab_result": 4.2})}
    assert types == {"Condition", "MedicationRequest", "AllergyIntolerance", "Observation"}


def test_empty_row_yields_nothing():
    assert shape_fhir(PA, {}) == []
    assert shape_fhir(FIN, {}) == []


# --- pseudonymisation ----------------------------------------------------------

def test_tokens_are_keyed_stable_and_non_reversible():
    a, b = token_for("MRN1", key="k1"), token_for("MRN1", key="k1")
    assert a == b and is_token(a) and "MRN1" not in a
    assert token_for("MRN1", key="k2") != a          # different export, different token


def test_only_direct_identifiers_are_replaced():
    out = pseudonymise_row(PA, ROW, key="k")
    assert is_token(out["mrn"]) and is_token(out["full_name"]) and is_token(out["phone"])
    assert out["date_of_birth"] == ROW["date_of_birth"]    # quasi-identifier, untouched
    assert out["sex"] == ROW["sex"] and out["admission_ward"] == ROW["admission_ward"]
    assert ROW["mrn"] == "MRN1234567"                       # input not mutated


# --- normalise + audit ---------------------------------------------------------

def _outputs():
    source = MockHISDataSource(records_per_layer=4, seed=5)
    return {t.name: t.extract(source, TASK) for t in DEFAULT_TECHNIQUES}


def test_manifest_claim_becomes_behaviour():
    outs = _outputs()
    compliant = normalise(outs["compliance-aware (ours)"], key="k")
    baseline = normalise(outs["unconstrained (baseline)"], key="k")
    assert compliant.pseudonymised and not baseline.pseudonymised
    patient = compliant.fhir[PA.value][0]
    assert is_token(patient["identifier"][0]["value"])
    raw_patient = baseline.fhir[PA.value][0]
    assert raw_patient["identifier"][0]["value"].startswith("MRN")


def test_compliant_export_leaks_no_raw_identifier_and_baseline_leaks_all():
    outs = _outputs()
    for name, out in outs.items():
        result = audit(out, normalise(out, key="k"))
        if name.startswith("compliance-aware"):
            assert result.clean and result.pseudonymisation_declared
        else:
            assert not result.clean
            assert result.leaked == result.identifier_values > 0


def test_shaping_follows_the_layer_standard_matrix():
    out = UnconstrainedExtractionTechnique().extract(MockHISDataSource(records_per_layer=2, seed=1), TASK)
    shaped = normalise(out, key="k")
    assert set(shaped.hl7) == {l.value for l in (PA, EHR, HISLayer.ANCILLARY_DEPARTMENTAL, FIN)}
    assert set(shaped.skipped_standards) == {"dicom", "iso_ieee_11073"}


def test_shaping_adds_nothing_that_was_not_extracted():
    # The compliant run pulled mrn, full_name, sex from PA -- the Patient resource
    # must not carry a birthDate or telecom it never saw.
    out = CompliantExtractionTechnique().extract(MockHISDataSource(records_per_layer=2, seed=1), TASK)
    shaped = normalise(out, key="k")
    for patient in shaped.fhir[PA.value]:
        assert set(patient) <= {"resourceType", "identifier", "name", "gender"}
    for msg in shaped.hl7[PA.value]:
        assert "PV1" not in msg                      # no ward was extracted


def test_summary_and_sample_render():
    out = CompliantExtractionTechnique().extract(MockHISDataSource(records_per_layer=2, seed=1), TASK)
    shaped = normalise(out, key="k")
    assert "HL7 v2 messages" in shaped.render_summary()
    sample = shaped.sample(PA)
    assert "MSH|" in sample and '"resourceType": "Patient"' in sample
    json.loads(json.dumps(shaped.fhir))            # serialisable
