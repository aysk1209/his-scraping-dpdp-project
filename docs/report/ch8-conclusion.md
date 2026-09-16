# Chapter 8 — Conclusion

*Draft 1, 2026-09-15. Target ~700 words; this draft runs ~950. The numbered
contribution list is written to become the last sentence of the manuscript's
abstract and the opening of Chapter 1; keep the three in step.*

---

We set out to treat compliance with the Digital Personal Data Protection Act,
2023 as a property of an extraction technique that can be measured, compared and
verified, rather than as a claim made about a system after it is built. The
framework, the benchmark and the pipeline that demonstrates them end to end are
the result. Nothing in them depends on live access to a hospital system, and
everything in them is regenerable from the repository with the commands given in
Appendix E.

## 8.1 Contributions

1. **A DPDP compliance framework as executable rules over an extraction
   manifest.** Seven principles of the Act, each a rule with a distinct check
   mechanism, scoring a structured declaration of what a run extracted, for what
   purpose, on what basis and under what safeguards. The rules see field
   categories and never values, so the artefacts they produce carry no personal
   data and the framework is independent of any particular hospital system.

2. **A two-axis benchmark whose cost measure is also a compliance measure.**
   Techniques are compared on compliance and on cost, metered identically at the
   adapter boundary in units that reproduce on any machine. The excess ratio —
   fields pulled over fields the purpose requires — is the data-minimisation
   overreach expressed as a cost; on our workload the compliant technique is the
   cheap one, and the pages the baseline pays for are exactly the overreach the
   law objects to. Coverage is the guard rail that catches a technique which
   scores well by pulling less than the task needs. Repeated runs give a
   determinism figure: a publicly available AI agent given the same job
   matches ours on the manifest it declares but takes different fields from
   the task's and reproduces its own decision in only two or three of five
   runs; ours reproduces it in five of five, by construction.

3. **The purpose matrix: compliance as a property of the pull and its purpose
   together.** One unchanged extraction, with a full manifest, is lawful under
   its declared purpose and unlawful under another — in both directions, because
   no purpose's scope contains another's. A technique cannot be compliant in the
   abstract, only for a stated purpose, and the framework makes that a result
   rather than a sentence.

4. **Content-based structure discovery.** A browser logs into a portal it was
   told nothing about, crawls it, and infers each module's HIS layer from the
   field names it finds, never from the URL; the same classification reads a
   hospital's exported files by their columns. Structure is discovered, not
   declared, and a new system is a new adapter with a label map, not a rewrite —
   which we regard as the answer to the heterogeneity doubt.

5. **Pseudonymisation on export, verified by audit.** Direct identifiers leave
   the system as keyed tokens, stable within an export and unlinkable across, and
   an audit searches the shaped HL7 v2 and FHIR artefacts for every raw value
   the run extracted. The manifest's claim and the output's property are reported
   side by side, so a declaration is never believed on its own word.

6. **A role gate derived from purposes and interoperability artefacts, applied
   to a staff assistant.** What a role may be told to do is the intersection of
   the purposes it acts under and the standard-defined artefacts it handles; the
   gate names the rule when it refuses and runs before any detail is collected.
   The assistant itself is rule-based and deliberately small; its value is that
   the same policy table that scores the benchmark visibly does work outside it.

## 8.2 What real data would change

The hospital dataset expected for the second review changes the *volume and
realism* of the evidence, not its shape. The compliance figures depend on
categories and manifests and are expected to hold; the field counts, the column
map, and any coverage ceiling imposed by a column the export lacks are the new
information, and the benchmark already reports the last as a property of the
source rather than of a technique. The handling gate ensures the data cannot be
read until its provenance and de-identification status are on record. Live
access to the hospital's own portal would additionally test the browser layer
against an interface we did not write, which is the one limitation the fixture
cannot close by itself.

## 8.3 What deployment would require, and why it is out of scope

Turning the pipeline into an operational tool would require a production
credential store, a scheduler, monitoring, a retention enforcer that actually
purges, and a mechanism for keeping the field catalogue and the label map in
step with a vendor's releases. None of this bears on the contribution, which is
the framework and the benchmark, and the project's scope was fixed to exclude
deployment on that ground. We note it so that the boundary is explicit rather
than implied.

## 8.4 Future work

Three extensions follow directly from decisions recorded in this report.

- **A fourth purpose, with its own envelope.** Claims adjudication was left
  unmodelled because it needs coded diagnosis data and would collapse the
  distinction between billing and care if folded into either. Modelled as its
  own purpose, it would preserve non-nesting — the test would enforce it — and
  give the `Claim` resource a role that may handle it.
- **DICOM and ISO/IEEE 11073 shaping.** Both standards are declared for the
  ancillary layer and reported as skipped. Shaping to them would extend the
  export audit to imaging and device data, where identifiers are embedded in
  headers rather than fields and pseudonymisation is harder to verify.
- **A portal we did not write.** The fixture demonstrates the mechanism; only a
  real interface demonstrates robustness. The label map and the generic
  selectors are designed for that transfer, and it is the first thing to do when
  live access arrives.

## 8.5 Closing

The compliant technique scores 1.000 and the baseline 0.135 on the same seven
rules; the compliant technique loads a fifth of the pages; the same extraction
is lawful for care and unlawful for billing; the compliant export contains no raw
identifier and the baseline's contains all of them; and a receptionist asking for
a diagnosis is refused, with the rule cited, before being asked for a name. Each
of these is a number or a decision the reader can regenerate. That — compliance
as something one measures rather than asserts — is what we set out to show.

---

*Cross-references to fill in at assembly: Chapter 1 (the contribution list,
stated in advance), Chapter 3 (§3.4 claims adjudication), Chapter 5 (the
handling gate; the fixture limitation), Chapter 7 (every number in §8.5).*
