"""FHIR R4 resource shaping -- hand-rolled dicts, only the elements we use.

One function per HIS layer returns the resources an extracted row supports. A
resource is emitted only when at least one of its elements was extracted, and an
element is present only when its field was. Nothing is defaulted or looked up, so
the resources carry exactly what the extraction pulled and no more.

    Patient Administration   -> Patient, Encounter
    Clinical / EHR           -> Encounter, Condition, MedicationRequest,
                                AllergyIntolerance, Observation (lab result)
    Ancillary / Departmental -> ServiceRequest, Observation, DiagnosticReport
    Administrative/Financial -> Invoice, Coverage

These are the resource types ``compliance.roles.ARTEFACTS`` names, so what a role
may be instructed to touch and what an export actually produces share one
vocabulary.
"""

from __future__ import annotations

from typing import Any

from interop.layers import HISLayer

IDENTIFIER_SYSTEM = "urn:his:mrn"
_GENDER = {"F": "female", "M": "male", "O": "other"}


def _present(row: dict[str, Any], *names: str) -> bool:
    return any(row.get(n) not in (None, "") for n in names)


def _patient(row: dict[str, Any]) -> dict[str, Any]:
    res: dict[str, Any] = {"resourceType": "Patient"}
    if row.get("mrn"):
        res["identifier"] = [{"system": IDENTIFIER_SYSTEM, "value": row["mrn"]}]
    if row.get("full_name"):
        res["name"] = [{"text": row["full_name"]}]
    if row.get("date_of_birth"):
        res["birthDate"] = row["date_of_birth"]
    if row.get("sex"):
        res["gender"] = _GENDER.get(str(row["sex"]).upper(), "unknown")
    telecom = []
    if row.get("phone"):
        telecom.append({"system": "phone", "value": row["phone"]})
    if row.get("email"):
        telecom.append({"system": "email", "value": row["email"]})
    if telecom:
        res["telecom"] = telecom
    if _present(row, "street_address", "pincode"):
        address: dict[str, Any] = {}
        if row.get("street_address"):
            address["line"] = [row["street_address"]]
        if row.get("pincode"):
            address["postalCode"] = str(row["pincode"])
        res["address"] = [address]
    return res


def _encounter(row: dict[str, Any]) -> dict[str, Any]:
    res: dict[str, Any] = {"resourceType": "Encounter", "status": "in-progress"}
    start = row.get("admission_datetime") or row.get("encounter_datetime")
    if start:
        res["period"] = {"start": start}
    if row.get("admission_ward"):
        res["class"] = {"code": "IMP", "display": "inpatient encounter"}
        res["location"] = [{"location": {"display": row["admission_ward"]}}]
    if row.get("attending_clinician"):
        res["participant"] = [{"individual": {"display": row["attending_clinician"]}}]
    return res


def shape_patient_administration(row: dict[str, Any]) -> list[dict[str, Any]]:
    out = []
    if _present(row, "mrn", "full_name", "date_of_birth", "sex", "phone", "email",
                "street_address", "pincode"):
        out.append(_patient(row))
    if _present(row, "admission_ward", "admission_datetime"):
        out.append(_encounter(row))
    return out


def shape_clinical(row: dict[str, Any]) -> list[dict[str, Any]]:
    out = []
    if _present(row, "encounter_datetime", "attending_clinician"):
        out.append(_encounter(row))
    if row.get("primary_diagnosis"):
        out.append({"resourceType": "Condition", "code": {"text": row["primary_diagnosis"]}})
    if row.get("medication"):
        out.append({"resourceType": "MedicationRequest", "status": "active", "intent": "order",
                    "medicationCodeableConcept": {"text": row["medication"]}})
    if row.get("allergy"):
        out.append({"resourceType": "AllergyIntolerance", "code": {"text": row["allergy"]}})
    if row.get("lab_result") not in (None, ""):
        out.append({"resourceType": "Observation", "status": "final",
                    "code": {"text": "laboratory result"},
                    "valueQuantity": {"value": row["lab_result"]}})
    return out


def shape_ancillary(row: dict[str, Any]) -> list[dict[str, Any]]:
    out = []
    if _present(row, "order_id", "specimen_type", "imaging_modality"):
        req: dict[str, Any] = {"resourceType": "ServiceRequest", "status": "active", "intent": "order"}
        if row.get("order_id"):
            req["identifier"] = [{"value": row["order_id"]}]
        if row.get("imaging_modality"):
            req["code"] = {"text": row["imaging_modality"]}
        if row.get("specimen_type"):
            req["specimen"] = [{"display": row["specimen_type"]}]
        out.append(req)
    if row.get("result_value") not in (None, ""):
        out.append({"resourceType": "Observation", "status": "final",
                    "code": {"text": "result"}, "valueQuantity": {"value": row["result_value"]}})
    if _present(row, "report_text", "imaging_modality") and row.get("report_text"):
        rep: dict[str, Any] = {"resourceType": "DiagnosticReport", "status": "final",
                               "conclusion": row["report_text"]}
        if row.get("imaging_modality"):
            rep["code"] = {"text": row["imaging_modality"]}
        out.append(rep)
    return out


def shape_financial(row: dict[str, Any]) -> list[dict[str, Any]]:
    out = []
    if _present(row, "invoice_id", "billed_amount"):
        inv: dict[str, Any] = {"resourceType": "Invoice", "status": "issued"}
        if row.get("invoice_id"):
            inv["identifier"] = [{"value": row["invoice_id"]}]
        if row.get("billed_amount") not in (None, ""):
            inv["totalGross"] = {"value": row["billed_amount"], "currency": "INR"}
        out.append(inv)
    if _present(row, "insurance_policy_no", "payer_name"):
        cov: dict[str, Any] = {"resourceType": "Coverage", "status": "active"}
        if row.get("insurance_policy_no"):
            cov["subscriberId"] = row["insurance_policy_no"]
        if row.get("payer_name"):
            cov["payor"] = [{"display": row["payer_name"]}]
        out.append(cov)
    return out


_SHAPERS = {
    HISLayer.PATIENT_ADMINISTRATION: shape_patient_administration,
    HISLayer.CLINICAL_EHR: shape_clinical,
    HISLayer.ANCILLARY_DEPARTMENTAL: shape_ancillary,
    HISLayer.ADMINISTRATIVE_FINANCIAL: shape_financial,
}


def shape_fhir(layer: HISLayer, row: dict[str, Any]) -> list[dict[str, Any]]:
    """The FHIR resources one extracted row of ``layer`` supports (possibly none)."""

    shaper = _SHAPERS.get(layer)
    return shaper(row) if shaper else []


def bundle(resources: list[dict[str, Any]]) -> dict[str, Any]:
    return {"resourceType": "Bundle", "type": "collection",
            "entry": [{"resource": r} for r in resources]}


__all__ = ["shape_fhir", "bundle", "shape_patient_administration", "shape_clinical",
           "shape_ancillary", "shape_financial", "IDENTIFIER_SYSTEM"]
