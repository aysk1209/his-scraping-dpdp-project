# Chapter 6 — Export and the staff assistant

*Draft 1, 2026-09-15. Target ~1400 words; this draft runs ~1900. No section of
the Act is cited here; the security-safeguards, purpose-limitation and
data-minimisation principles are established in §3.3.*

---

The policy table of §3.4 scores an extraction. This chapter shows it gating two
more things: **what leaves the system** as interoperable artefacts, and **what a
member of staff may be told to do.** The two are the same check applied at
different points, and the chapter's claim is that a compliance layer earns its
name when it does work outside the benchmark — when the manifest's promise about
the output is verified against the output (§6.2), and when a request from the
wrong role is refused by the same table that scored the benchmark (§6.3–§6.4).

## 6.1 Shaping adds nothing

A run's rows are shaped on the way out into the interoperability standards that
carry each HIS layer — HL7 v2 messages and FHIR resources, per a fixed
layer-to-standard matrix (`src/interop/mapping.py`): Patient Administration to
`ADT^A04` and `Patient`/`Encounter`; Clinical to `ORM^O01` and `Condition`,
`MedicationRequest`, `AllergyIntolerance`, `Observation`; Ancillary to `ORU^R01`
and `ServiceRequest`, `Observation`, `DiagnosticReport`; Administrative /
Financial to `DFT^P03` and `Invoice`, `Coverage`; the audit layer to
`AuditEvent`, which has no HL7 v2 counterpart. DICOM and ISO/IEEE 11073 are
declared for the ancillary layer and reported as skipped in this phase. The
shapers are hand-rolled for our records (`src/interop/hl7/`, `fhir/`), following
the segment and resource definitions for the handful of fields the project uses;
they are not general libraries, and no vendor's implementation is involved.

The property that matters is that **shaping adds nothing**. A builder sets only
the fields present in the row. A field that was not extracted is not invented,
not defaulted and not looked up — so a message or resource carries exactly what
the extraction pulled, and the data-minimisation property of the extraction
survives the export. An `ADT^A04` from the compliant technique's patient-summary
run has a `PID` segment with a medical record number, a date of birth and a sex,
and nothing else; the corresponding `Patient` resource has an identifier, a
`birthDate` and a `gender`. `test_shaping_adds_nothing_that_was_not_extracted`
asserts this for every layer.

## 6.2 Pseudonymisation on export, and the audit

The compliant technique *declares* in its manifest that direct identifiers are
pseudonymised on export, and SS-01 credits the declaration. This is where the
declaration becomes behaviour, and where it is checked.

**Pseudonymisation** (`src/compliance/pseudonymise.py`) replaces every field the
catalogue classes as a direct identifier — medical record number, name, phone,
the subject of an audit event — with a keyed token before the row is shaped. The
token is a keyed hash of the value, truncated and prefixed (`PSN-…`). It is
pseudonymisation, not anonymisation: the same value yields the same token
*within one export*, so records about one patient stay linkable to each other,
which is what an interoperable export is for; and the key is the export's
secret, so without it the token cannot be reversed and a fresh hash of the real
value will not match it, which makes exports **unlinkable across** each other.
Pseudonymisation is applied exactly when the run's manifest declares it —
`normalise` reads the manifest and does nothing else — so the behaviour cannot
drift from the claim.

**The export audit** (`normalise.audit`) is the verification. It collects every
raw direct-identifier value the run extracted, from the rows the technique
returned, and searches the shaped artefacts — every encoded HL7 v2 message,
every serialised FHIR resource — for each of them verbatim. The result is
counted: identifiers extracted, identifiers found in the export, artefacts
checked. On the pipeline's default run the compliant technique's export is
searched for its 20 identifiers across 120 artefacts and none is found; the
baseline's is searched for its 80 across 340 and all 80 are found (Chapter 7,
Table 5). The declaration in the manifest and the property of the output agree
in both cases.

This is the division of labour between rule and audit that §3.2 anticipated.
The rules see categories and score a *claim*; the audit sees values and checks
a *fact*. A technique that declared pseudonymisation and did not perform it
would score 1.0 on SS-01 and fail the audit, and the pipeline reports both side
by side so that a manifest cannot be believed on its own word. One consequence
is applied to our own outputs: the pipeline writes only the pseudonymised export
to disk. The baseline's raw one is shaped, audited and discarded, because on
real data that file would itself be the leak the audit reports.

## 6.3 Role access, derived

Who may be told to do what is the second application of the policy. A role's
access (`src/compliance/roles.py`) is **derived, not listed**, from two
independent sources:

1. **The purposes a role acts under.** A nurse acts for care coordination; an
   administrator for billing settlement and registration; reception for
   registration and, for eligibility checks, billing settlement. A role has no
   access to data outside its purposes' envelopes, so the gate *is* purpose
   limitation applied to a person rather than to an extraction.
2. **The interoperability artefacts a role handles.** HL7 v2 message types,
   FHIR resource types, DICOM studies, ISO/IEEE 11073 device observations, each
   declared with the data categories it carries. The team's working assumption
   is that access follows the standards: a role may touch a category only where
   some artefact it legitimately handles carries it.

A role's effective scope is the **intersection**. Either source alone would
over-grant, and the tests show both cases: purpose alone would let reception,
which acts under billing for eligibility, be walked through raising an invoice
— but reception handles `Coverage` and not `Invoice` or `Account`, so it
cannot; artefacts alone would let the nurse read a patient's address from
`Patient` — but care coordination does not make contact data necessary, so it
cannot.

`authorise(role, purpose, artefacts)` is the gate, and it applies three checks
in the order a data-protection officer would ask them, each a principle, each
naming its rule when it refuses:

| Question | Refused as | Example |
|---|---|---|
| Is there a lawful purpose for this role? | PL-01 | reception asking for a diagnosis |
| Is every category necessary for that purpose? | DM-01 | anyone touching `Claim` under billing — it carries coded diagnosis |
| Does this role handle these artefacts under the standards? | SS-01 | reception raising an `Invoice` |

An artefact the vocabulary does not describe is refused before anything is
derived from it: unassessable access is not safe access.

Three artefacts are in the vocabulary and **granted to no role, by design**.
`fhir:Claim` carries coded diagnosis, and claims adjudication is the purpose
§3.4 deliberately left unmodelled; `dicom:Study`, because no imaging role is
modelled; `fhir:AuditEvent`, because the audit log is reviewed by a
data-protection role, not by front-line staff. They are kept so that the gate is
seen refusing them for the right reason rather than because they are unknown —
the last row of Table 6 in Chapter 7 is the administrator being refused a claim
under DM-01, not under an error.

## 6.4 The assistant

The staff-guidance assistant (`src/agent/`) is the deliverable that makes the
project complete, and we say plainly what it is and is not. It is **rule-based
and deterministic: no language model, no training, no external service.** It
recognises a pre-defined function from what a staff member types, asks for the
details that function needs, and replies with templated instructions. It is a
completeness deliverable, not a research contribution, and it has exactly one
research-relevant property: its function registry is gated per role by
`authorise`, so a receptionist asking how to look up a diagnosis is declined by
the same policy table that scored the extraction benchmark.

**The registry.** Thirteen functions across the three roles — registering a
patient, booking, check-in and insurance verification at the desk; vitals,
medications, diagnosis, lab requests and discharge on the ward; bed allocation,
invoicing, reconciliation and the census in administration. Each declares the
purpose it serves, the artefacts it touches, the inputs it needs, and its steps
as templates over those inputs, every step grounded in a HIS layer, an artefact
and catalogue field names. *Who may perform a function is not stored.* It falls
out of `authorise`, so there is one place where access is decided and the
registry cannot drift from it.

**Recognition** is token overlap between the request and each function's label
and synonyms — nothing more. It cannot invent a function that does not exist,
and when two functions tie it asks which was meant rather than guessing.

**The gate runs before any input is collected.** The session is a small state
machine — recognise, gate, collect, instruct — and the order is a compliance
decision. If the role may not be guided through a function, the assistant
declines at once, cites the rule, and names the role that can; it never asks for
the patient's name or medical record number first. Collecting details for a
request you are about to refuse is itself over-collection.
`test_gate_runs_before_any_input_is_requested` asserts the ordering.

**Grounded steps.** The answer is numbered steps, each stating the layer and
artefact it touches, the fields it uses, a caution where a step touches a
sensitive category, and — when the crawler of Chapter 5 has run — the portal
page on which the step happens, taken from the navigation map. A footer states
the purpose the guidance was given for, the legitimate use it rests on, the
categories touched and the retention ceiling, so that the answer carries its
own compliance context. Tests assert groundedness against the artefact
vocabulary and the field catalogue: an instruction cannot refer to something
the HIS model lacks.

The assistant is small by decision and will stay so. Its value to the project
is the moment in Chapter 7's Table 6 where the compliance layer visibly does
work outside the benchmark — a decline, with the rule cited, before a single
detail is asked for.

---

*Cross-references to fill in at assembly: Chapter 3 (§3.2 the rule–audit
division; §3.3.4 SS-01; §3.4 claims adjudication unmodelled), Chapter 5 (the
navigation map and page placement; the audit layer), Chapter 7 (Table 5 the
audit; Table 6 the role gate).*
