"""Demo: what each staff role may be instructed to do, and why not otherwise.

    python scripts/show_role_access.py

Prints each role's derived scope -- the purposes it acts under, the
interoperability artefacts it handles, and the data categories that leaves it --
then puts one request through the gate for all three roles at once, so the same
action produces three different answers for three different reasons.

This is the compliance half of the staff-guidance agent (build step 6). The
agent itself will call ``compliance.roles.authorise`` before it says anything;
this script shows that call working on its own.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import _present as present
from compliance.models import FieldCategory, Purpose
from compliance.roles import (
    ARTEFACTS,
    StaffRole,
    authorise,
    describe,
    unassigned_artefacts,
)

_SCENARIO = """\
Three staff roles, three purposes, one policy. A role's access is derived, not
listed: it may touch a data category only where (a) a purpose it lawfully acts
under makes the category necessary AND (b) an artefact it handles under HL7 /
FHIR / DICOM / ISO-IEEE-11073 carries it. Either source alone would over-grant."""

REQUESTS = [
    ("Raise an invoice for the visit",
     Purpose.BILLING_SETTLEMENT, {"fhir:Invoice", "fhir:Account"}, None),
    ("Look up the patient's diagnosis and medication",
     Purpose.CARE_COORDINATION, {"fhir:Condition", "fhir:MedicationRequest"}, None),
    ("Check whether the patient's insurance is active",
     Purpose.BILLING_SETTLEMENT, {"fhir:Coverage"}, None),
    ("Match the patient at the desk by name and date of birth",
     Purpose.PATIENT_REGISTRATION, {"fhir:Patient"},
     {FieldCategory.DIRECT_IDENTIFIER, FieldCategory.QUASI_IDENTIFIER}),
    ("Reconcile an insurance claim, including the diagnosis codes",
     Purpose.BILLING_SETTLEMENT, {"fhir:Claim"}, None),
]


def main() -> None:
    print(present.banner("Role-based access - derived from purpose and interop standards"))
    print(_SCENARIO)
    print(present.rule())

    for role in StaffRole:
        print(describe(role))
        print()

    withheld = ", ".join(f"{k} ({ARTEFACTS[k].name})" for k in unassigned_artefacts())
    print(f"Granted to no role, by design: {withheld}")
    print(present.rule())

    print("The same request, all three roles:")
    for label, purpose, artefacts, categories in REQUESTS:
        print()
        print(f"  \"{label}\"")
        print(f"    purpose {purpose.value}; artefacts {', '.join(sorted(artefacts))}")
        for role in StaffRole:
            decision = authorise(role, purpose, artefacts, categories)
            print(f"    {role.value:<14} {decision.one_line()}")

    print(present.rule())
    print(
        "Every decline names the rule that produced it. The agent will make exactly\n"
        "this call before it answers, so a receptionist asking about a diagnosis is\n"
        "declined by the same policy table that scores the extraction benchmark."
    )


if __name__ == "__main__":
    main()
