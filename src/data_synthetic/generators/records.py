"""Minimal synthetic HIS record generator (build step 3, thin slice).

Produces plain-dict records with placeholder-realistic values for every field in
``data_synthetic.catalogue.FIELD_CATALOGUE``. Values are Faker-generated and
carry no meaning -- no real patients, no real hospital distributions. Seeded for
reproducible demos and tests.

Full per-layer pydantic schemas and HL7/FHIR shaping are deferred to the full
build step 3.
"""

from __future__ import annotations

from typing import Any

from faker import Faker

from data_synthetic.catalogue import FIELD_CATALOGUE
from interop.layers import HISLayer

_DIAGNOSES = (
    "Type 2 diabetes mellitus",
    "Essential hypertension",
    "Acute bronchitis",
    "Iron deficiency anaemia",
)
_MEDICATIONS = (
    "Metformin 500mg",
    "Amlodipine 5mg",
    "Amoxicillin 500mg",
    "Ferrous sulfate 200mg",
)


def _value_for(field: str, fake: Faker) -> Any:
    match field:
        case "mrn":
            return f"MRN{fake.random_number(digits=7, fix_len=True)}"
        case "full_name" | "attending_clinician":
            return fake.name()
        case "phone":
            return fake.numerify("+91-##########")
        case "email":
            return fake.ascii_email()
        case "street_address":
            return fake.street_address().replace("\n", ", ")
        case "date_of_birth":
            return fake.date_of_birth(minimum_age=0, maximum_age=95).isoformat()
        case "sex":
            return fake.random_element(("F", "M", "O"))
        case "pincode":
            return fake.numerify("######")
        case "admission_ward":
            return fake.random_element(("Ward A", "Ward B", "ICU", "Day Care"))
        case "admission_datetime" | "encounter_datetime":
            return fake.date_time_this_year().isoformat(timespec="seconds")
        case "primary_diagnosis":
            return fake.random_element(_DIAGNOSES)
        case "medication":
            return fake.random_element(_MEDICATIONS)
        case "lab_result" | "result_value":
            return round(fake.random.uniform(0.1, 15.0), 1)
        case "allergy":
            return fake.random_element(("None known", "Penicillin", "Sulfa drugs", "Latex"))
        case "specimen_type":
            return fake.random_element(("Blood", "Urine", "Swab", "Tissue"))
        case "imaging_modality":
            return fake.random_element(("XR", "CT", "MRI", "US"))
        case "report_text":
            return fake.sentence(nb_words=12)
        case "order_id":
            return f"ORD{fake.random_number(digits=8, fix_len=True)}"
        case "invoice_id":
            return f"INV{fake.random_number(digits=8, fix_len=True)}"
        case "billed_amount":
            return round(fake.random.uniform(100.0, 90000.0), 2)
        case "insurance_policy_no":
            return fake.bothify("??########").upper()
        case "payer_name":
            return fake.company()
        case _:  # pragma: no cover - guards against a catalogue field with no recipe
            return fake.word()


def generate_layer_records(
    layer: HISLayer, n: int, *, seed: int | None = None
) -> list[dict[str, Any]]:
    """Generate ``n`` records for one HIS layer, one value per catalogue field."""

    fake = Faker()
    if seed is not None:
        fake.seed_instance(seed)
    fields = FIELD_CATALOGUE[layer]
    return [{name: _value_for(name, fake) for name in fields} for _ in range(n)]


def build_dataset(
    records_per_layer: int, *, seed: int | None = None
) -> dict[HISLayer, list[dict[str, Any]]]:
    """Generate a full synthetic dataset: records for every catalogue layer.

    Each layer is seeded with a distinct offset of ``seed`` so layers do not
    share an identical value sequence.
    """

    return {
        layer: generate_layer_records(
            layer, records_per_layer, seed=None if seed is None else seed + offset
        )
        for offset, layer in enumerate(FIELD_CATALOGUE)
    }
