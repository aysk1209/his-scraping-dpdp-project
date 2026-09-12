"""HL7 v2 message shaping -- hand-rolled, pipe-and-hat encoded, no transport.

A minimal segment model (``Segment``, ``Message``) and one builder per HIS layer
that has an HL7 v2 message type in ``interop.mapping``:

    Patient Administration   -> ADT^A04  (register a patient)
    Clinical / EHR           -> ORM^O01  (order, with diagnosis, allergy, medication)
    Ancillary / Departmental -> ORU^R01  (observation result)
    Administrative/Financial -> DFT^P03  (detail financial transaction)

Builders set only the fields present in the row. A field that was not extracted is
not invented, not defaulted, not looked up -- so the message carries exactly what
the extraction pulled, and the data-minimisation property of the extraction
survives shaping. Field positions follow the HL7 v2.5 segment definitions for the
handful of fields the project uses; this is a shaper for our records, not a
general HL7 library.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from interop.layers import HISLayer

FIELD_SEP = "|"
COMPONENT_SEP = "^"
SEGMENT_SEP = "\r"
ENCODING_CHARS = "^~\\&"
VERSION = "2.5"
SENDING_APP = "EXTRACTION"
SENDING_FACILITY = "HIS"


class Segment:
    """One segment: a name and positionally numbered fields (1-based, HL7 style)."""

    def __init__(self, name: str) -> None:
        self.name = name
        self._fields: dict[int, str] = {}

    def set(self, index: int, value: Any) -> "Segment":
        if value is None or value == "":
            return self
        self._fields[index] = str(value)
        return self

    def has_data(self) -> bool:
        # Anything beyond a set-id in field 1 counts as content.
        return any(i > 1 for i in self._fields)

    def encode(self) -> str:
        if self.name == "MSH":
            # MSH-1 is the field separator itself; MSH-2 the encoding characters.
            width = max(self._fields, default=2)
            fields = [self._fields.get(i, "") for i in range(3, width + 1)]
            return FIELD_SEP.join(["MSH", ENCODING_CHARS, *fields])
        width = max(self._fields, default=0)
        fields = [self._fields.get(i, "") for i in range(1, width + 1)]
        return FIELD_SEP.join([self.name, *fields])


class Message:
    def __init__(self, message_type: str, control_id: str, *, when: datetime | None = None) -> None:
        when = when or datetime.now(timezone.utc)
        self.message_type = message_type
        self.segments: list[Segment] = []
        self.segments.append(
            Segment("MSH")
            .set(3, SENDING_APP).set(4, SENDING_FACILITY)
            .set(7, when.strftime("%Y%m%d%H%M%S"))
            .set(9, message_type).set(10, control_id).set(11, "P").set(12, VERSION)
        )

    def add(self, segment: Segment) -> "Message":
        if segment.has_data():
            self.segments.append(segment)
        return self

    def encode(self) -> str:
        return SEGMENT_SEP.join(s.encode() for s in self.segments)

    def segment_names(self) -> list[str]:
        return [s.name for s in self.segments]


def _hl7_date(value: Any) -> str | None:
    if not value:
        return None
    return str(value).replace("-", "").replace(":", "").replace("T", "")[:14]


# --------------------------------------------------------------------------- #
# Builders
# --------------------------------------------------------------------------- #

def _pid(row: dict[str, Any]) -> Segment:
    pid = Segment("PID").set(1, "1")
    if row.get("mrn"):
        pid.set(3, f"{row['mrn']}{COMPONENT_SEP*3}{SENDING_FACILITY}{COMPONENT_SEP}MR")
    if row.get("full_name"):
        parts = str(row["full_name"]).split()
        if len(parts) > 1:
            pid.set(5, f"{parts[-1]}{COMPONENT_SEP}{' '.join(parts[:-1])}")
        else:                       # a single name -- or a pseudonymisation token
            pid.set(5, parts[0])
    pid.set(7, _hl7_date(row.get("date_of_birth")))
    pid.set(8, row.get("sex"))
    if row.get("street_address") or row.get("pincode"):
        pid.set(11, f"{row.get('street_address', '')}{COMPONENT_SEP*4}{row.get('pincode', '')}")
    if row.get("phone") or row.get("email"):
        pid.set(13, f"{row.get('phone', '')}{COMPONENT_SEP*3}{row.get('email', '')}")
    return pid


def adt_a04(row: dict[str, Any], control_id: str) -> Message:
    """Register a patient -- Patient Administration layer."""

    msg = Message("ADT^A04", control_id)
    msg.add(Segment("EVN").set(1, "A04").set(2, _hl7_date(row.get("admission_datetime"))))
    msg.add(_pid(row))
    msg.add(Segment("PV1").set(1, "1").set(2, "I" if row.get("admission_ward") else None)
            .set(3, row.get("admission_ward")).set(44, _hl7_date(row.get("admission_datetime"))))
    return msg


def orm_o01(row: dict[str, Any], control_id: str) -> Message:
    """Clinical order with the visit's diagnosis, allergy and medication."""

    msg = Message("ORM^O01", control_id)
    msg.add(Segment("PV1").set(1, "1").set(7, row.get("attending_clinician"))
            .set(44, _hl7_date(row.get("encounter_datetime"))))
    msg.add(Segment("AL1").set(1, "1").set(3, row.get("allergy")))
    msg.add(Segment("DG1").set(1, "1").set(3, row.get("primary_diagnosis")))
    if row.get("medication"):
        msg.add(Segment("ORC").set(1, "NW"))
        msg.add(Segment("RXO").set(1, row.get("medication")))
    if row.get("lab_result") not in (None, ""):
        msg.add(Segment("OBX").set(1, "1").set(2, "NM").set(3, "LAB").set(5, row.get("lab_result")))
    return msg


def oru_r01(row: dict[str, Any], control_id: str) -> Message:
    """Departmental result -- Ancillary layer."""

    msg = Message("ORU^R01", control_id)
    msg.add(Segment("OBR").set(1, "1").set(2, row.get("order_id"))
            .set(4, row.get("imaging_modality")).set(15, row.get("specimen_type")))
    if row.get("result_value") not in (None, ""):
        msg.add(Segment("OBX").set(1, "1").set(2, "NM").set(3, "RESULT").set(5, row.get("result_value")))
    msg.add(Segment("NTE").set(1, "1").set(3, row.get("report_text")))
    return msg


def dft_p03(row: dict[str, Any], control_id: str) -> Message:
    """Detail financial transaction -- Administrative / Financial layer."""

    msg = Message("DFT^P03", control_id)
    msg.add(Segment("EVN").set(1, "P03"))
    msg.add(Segment("FT1").set(1, "1").set(2, row.get("invoice_id")).set(6, "CG")
            .set(11, row.get("billed_amount")))
    msg.add(Segment("IN1").set(1, "1").set(4, row.get("payer_name"))
            .set(36, row.get("insurance_policy_no")))
    return msg


_BUILDERS = {
    HISLayer.PATIENT_ADMINISTRATION: adt_a04,
    HISLayer.CLINICAL_EHR: orm_o01,
    HISLayer.ANCILLARY_DEPARTMENTAL: oru_r01,
    HISLayer.ADMINISTRATIVE_FINANCIAL: dft_p03,
}


def shape_hl7(layer: HISLayer, row: dict[str, Any], control_id: str) -> Message | None:
    """The HL7 v2 message for one extracted row of ``layer``, or None if no type applies."""

    builder = _BUILDERS.get(layer)
    return builder(row, control_id) if builder else None


__all__ = ["Segment", "Message", "adt_a04", "orm_o01", "oru_r01", "dft_p03", "shape_hl7"]
