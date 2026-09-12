"""Normalise an extraction into interoperability artefacts, and audit the export.

This is the pipeline's export stage. It takes a technique's output -- the manifest
and the raw rows it pulled -- and shapes each row into the standards its layer
carries (``interop.mapping.LAYER_STANDARDS``): HL7 v2 messages and FHIR resources.
DICOM and ISO/IEEE 11073 are still stubs and are skipped.

Two things make this compliance work rather than plumbing:

1. **The manifest's claim becomes behaviour.** If the run declared
   ``security.identifiers_pseudonymised``, direct identifiers are replaced by keyed
   tokens *before* shaping. The compliant technique declares it; the baseline does
   not; the exports differ accordingly.

2. **The export is audited, not trusted.** ``audit()`` searches every emitted
   artefact for the raw direct-identifier values that were extracted, and counts
   the leaks. A compliant export leaks none; the baseline's leaks every one. This
   turns SS-01's pseudonymisation check from a declaration the rule takes on faith
   into a property verified against the actual output.

# DPDP Act 2023 -- security safeguards (pseudonymisation on export) and data
# minimisation (shaping adds nothing that was not extracted).
"""

from __future__ import annotations

import json
import secrets
from typing import Any

from pydantic import BaseModel, Field

from compliance.pseudonymise import direct_identifier_fields, pseudonymise_row
from extraction.technique import TechniqueOutput
from interop.fhir.resources import shape_fhir
from interop.hl7.messages import shape_hl7
from interop.layers import HISLayer
from interop.mapping import InteropStandard, standards_for


class ExportAudit(BaseModel):
    """Did any raw direct identifier reach the exported artefacts?"""

    pseudonymisation_declared: bool
    identifier_values: int             # distinct raw direct-identifier values extracted
    leaked: int                        # of those, how many appear verbatim in an artefact
    artefacts_checked: int

    @property
    def clean(self) -> bool:
        return self.leaked == 0

    def one_line(self) -> str:
        state = "declared" if self.pseudonymisation_declared else "not declared"
        verdict = "no raw identifiers in the export" if self.clean else (
            f"{self.leaked} of {self.identifier_values} raw identifiers appear in the export"
        )
        return f"pseudonymisation {state}; {verdict} ({self.artefacts_checked} artefacts checked)"


class NormalisedOutput(BaseModel):
    run_id: str
    pseudonymised: bool
    hl7: dict[str, list[str]] = Field(default_factory=dict)              # layer -> encoded messages
    fhir: dict[str, list[dict[str, Any]]] = Field(default_factory=dict)  # layer -> resources
    skipped_standards: list[str] = Field(default_factory=list)

    def counts(self) -> dict[str, int]:
        return {
            "hl7_messages": sum(len(v) for v in self.hl7.values()),
            "fhir_resources": sum(len(v) for v in self.fhir.values()),
        }

    def sample(self, layer: HISLayer) -> str:
        """One HL7 message and one FHIR resource for ``layer``, for a reader."""

        lines: list[str] = []
        msgs = self.hl7.get(layer.value) or []
        if msgs:
            lines.append("  HL7 v2:")
            lines += ["    " + seg for seg in msgs[0].split("\r")]
        res = self.fhir.get(layer.value) or []
        if res:
            lines.append("  FHIR:")
            lines += ["    " + l for l in json.dumps(res[0], indent=2).split("\n")]
        return "\n".join(lines) if lines else "  (nothing shaped for this layer)"

    def render_summary(self) -> str:
        c = self.counts()
        lines = [
            f"normalised '{self.run_id}': {c['hl7_messages']} HL7 v2 messages, "
            f"{c['fhir_resources']} FHIR resources"
            + ("; direct identifiers pseudonymised" if self.pseudonymised else "; identifiers raw"),
        ]
        for layer_value in sorted(set(self.hl7) | set(self.fhir)):
            h = len(self.hl7.get(layer_value, []))
            f = len(self.fhir.get(layer_value, []))
            lines.append(f"  {layer_value:<26} {h:>5} HL7   {f:>5} FHIR")
        if self.skipped_standards:
            lines.append("  skipped (stubs this phase): " + ", ".join(sorted(set(self.skipped_standards))))
        return "\n".join(lines)


def normalise(output: TechniqueOutput, *, key: str | None = None) -> NormalisedOutput:
    """Shape a technique's rows into HL7 v2 and FHIR, per the layer's standards.

    Pseudonymisation is applied exactly when the run's manifest declares it; the
    ``key`` is the export's secret and defaults to a fresh random one.
    """

    pseudonymise = output.run.security.identifiers_pseudonymised
    key = key or secrets.token_hex(16)
    result = NormalisedOutput(run_id=output.run.run_id, pseudonymised=pseudonymise)

    for layer_value, rows in output.rows.items():
        layer = HISLayer(layer_value)
        standards = standards_for(layer)
        for n, raw in enumerate(rows, start=1):
            row = pseudonymise_row(layer, raw, key=key) if pseudonymise else raw
            if InteropStandard.HL7_V2 in standards:
                msg = shape_hl7(layer, row, control_id=f"{output.run.run_id}-{layer_value}-{n}")
                if msg is not None:
                    result.hl7.setdefault(layer_value, []).append(msg.encode())
            if InteropStandard.FHIR in standards:
                shaped = shape_fhir(layer, row)
                if shaped:
                    result.fhir.setdefault(layer_value, []).extend(shaped)
        for std in standards:
            if std not in (InteropStandard.HL7_V2, InteropStandard.FHIR):
                result.skipped_standards.append(std.value)

    return result


def audit(output: TechniqueOutput, normalised: NormalisedOutput) -> ExportAudit:
    """Search the export for the raw direct-identifier values that were extracted."""

    corpus: list[str] = []
    for msgs in normalised.hl7.values():
        corpus.extend(msgs)
    for resources in normalised.fhir.values():
        corpus.extend(json.dumps(r) for r in resources)
    haystack = "\n".join(corpus)

    values: set[str] = set()
    for layer_value, rows in output.rows.items():
        fields = direct_identifier_fields(HISLayer(layer_value))
        for row in rows:
            for name in fields:
                v = row.get(name)
                if v not in (None, ""):
                    values.add(str(v))

    leaked = sum(1 for v in values if v in haystack)
    return ExportAudit(
        pseudonymisation_declared=output.run.security.identifiers_pseudonymised,
        identifier_values=len(values),
        leaked=leaked,
        artefacts_checked=len(corpus),
    )


__all__ = ["normalise", "audit", "NormalisedOutput", "ExportAudit"]
