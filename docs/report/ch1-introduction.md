# Chapter 1 — Introduction

*Draft 1, 2026-09-15. Target ~900 words; this draft runs ~1250. The
contribution list in §1.4 is the one in §8.1, stated in advance; keep the two in
step. No section of the Act is cited here — the Act is introduced by name and its
provisions are established in Chapters 2 and 3.*

---

## 1.1 Motivation

Hospital Information Systems hold some of the most sensitive personal data any
organisation processes: who a person is, where they live, what they were
diagnosed with, what they were prescribed, what they were billed and who paid. A
great deal of useful work depends on getting that data *out* of the system —
into a report, a message to another system, a summary for a clinician, an
answer for the front desk — and where a system offers no programmatic interface,
or none that a hospital can afford to integrate against, the practical route is
extraction through the interface that exists: the portal a member of staff logs
into.

Techniques for that kind of extraction are well studied. They are evaluated,
almost without exception, on three things: how fast they run, how robust they
are to changes in the interface, and how much of the available data they
recover. Coverage is treated as the goal and more of it as better. What none of
that evaluation asks is whether the extraction *should* have taken what it
took — whether the data pulled was necessary for the purpose it was pulled for,
whether the person it concerns was told, whether it will be deleted, whether
anyone is answerable for it.

In India those questions stopped being optional with the Digital Personal Data
Protection Act, 2023. The Act binds any organisation that processes digital
personal data to a set of obligations — process only for a lawful and specified
purpose, take only what that purpose needs, give notice, keep data no longer
than necessary, safeguard it, and be able to demonstrate all of this — and a
hospital extracting its own patients' data through a portal is processing
personal data in exactly the Act's sense. An extraction technique that is tuned
for coverage and evaluated on coverage is, under the Act, tuned to over-collect
and evaluated on how thoroughly it does so.

That is a legal exposure for the hospital and a research gap at the same time.
The gap is not that compliance is ignored — it is that compliance is treated as
something assessed *about a system afterwards*, in a policy document or an
audit, rather than as a property of the *technique* that can be designed for,
measured, and compared across techniques the way speed and coverage are.

## 1.2 The applied setting

The project's motivating application is an assistant for hospital staff: a
system that understands the structure of a hospital's information system well
enough to tell a receptionist, a nurse or an administrator how to perform a
task in it, in plain steps, differentiated by role. Such an assistant has to
know where things are — which module holds registrations, which holds orders,
which fields live on which pages — and that knowledge has to come from
somewhere. It comes from extraction. The assistant is therefore the reason
extraction matters here, and it also supplies the project's second use of the
same idea: what a member of staff may be *told* to do with personal data is
governed by the same obligations as what a program may *take*. A receptionist
has no lawful reason to see a diagnosis, and an assistant that explained how to
find one would be instructing a breach.

The assistant is built and it runs, but we are explicit throughout this report
that it is not the contribution. It is deliberately simple — rule-based, with no
language model and no training — and its one research-relevant property is
that it is gated by the compliance layer that the rest of the report is about.

## 1.3 Thesis

The thesis of this work is that **compliance with the Digital Personal Data
Protection Act, 2023 can be a measured, benchmarkable property of an extraction
technique.** Concretely: that the Act's principles can be written as executable
rules over a structured declaration of what an extraction did and why; that any
technique can be scored by those rules on equal terms; that the score
discriminates between techniques and not merely between careful and careless
configurations of one; that it can be set beside a cost measure and the two
read together; and that the same rules, applied at the point where data leaves
the system and at the point where a person is instructed, do work outside the
benchmark that a reader can see.

We show this without live access to a hospital system and without a
hospital's data, which — being the personal data of its patients — may never be
released to a student project, and which we do not assume. Every result is
produced against synthetic data of a realistic structure, served through a
login-gated portal fixture that a real browser scrapes, and against a public
export we did not generate; every result is regenerable from the repository. A
hospital export, if one is released, is read by the same pipeline with its own
column map; nothing in the argument depends on it.

## 1.4 Contributions

The report makes six contributions, developed in Chapters 3 to 6 and evaluated
in Chapter 7. They are stated here in the form in which Chapter 8 returns to
them.

1. **A DPDP compliance framework as executable rules over an extraction
   manifest** — seven principles, seven rules with distinct check mechanisms,
   scoring a declaration rather than an intention, and never seeing a value.
2. **A two-axis benchmark whose cost measure is also a compliance measure** —
   the excess ratio, fields pulled over fields the purpose requires, is the
   data-minimisation overreach expressed as a cost, with coverage as the guard
   rail — and, beyond it, whether a technique's declarations are ones the
   deployment can back, whether it holds the line when the wording asks for
   more than the purpose permits, and whether it reproduces its own decision.
   These are what separate a rule-driven technique from publicly available AI
   models that match it on paperwork.
3. **The purpose matrix** — one unchanged extraction, lawful under its declared
   purpose and unlawful under another, in both directions: compliance as a
   property of the pull and its purpose together.
4. **Content-based structure discovery** — a browser infers each portal
   module's HIS layer from the field names it finds, never from the URL, and the
   same classification reads an export's files — a public one we did not write
   among them.
5. **Pseudonymisation on export, verified by audit** — the manifest's claim
   about the output checked against the output, so a declaration is never
   believed on its own word.
6. **A role gate derived from purposes and interoperability artefacts** —
   applied to the staff assistant, refusing out-of-role requests with the rule
   cited and before any detail is collected.

## 1.5 Scope

Three boundaries are fixed and stated. Deployment is not in scope: the
contribution is the framework and the benchmark, not an operational tool.
Live access to a hospital system is not assumed: the pipeline is complete and
runnable without it, and treats it as upside. And the assistant is a
completeness deliverable: it is built to work and kept small, and it is not
benchmarked.

## 1.6 Structure of the report

Chapter 2 gives the background: the Act and its principles, the five-layer
model of a hospital information system and the interoperability standards that
carry each layer, and the extraction literature this work extends. Chapter 3
presents the compliance framework — the manifest, the valueless record
representation, the seven rules, the purpose policy and the aggregated score —
and is the core of the report. Chapter 4 presents the three techniques under
comparison and the cost axis, and argues that the excess ratio and the
minimisation rule are one quantity seen twice. Chapter 5 covers acquisition:
the portal fixture, browser-driven extraction with layer inference, the dataset
adapter and the handling gate for real data. Chapter 6 follows the data out —
shaping into HL7 v2 and FHIR, pseudonymisation and its audit — and applies the
same policy to staff roles and the assistant. Chapter 7 evaluates: six tables,
each regenerable, and a stated set of threats to validity. Chapter 8 concludes
with the contributions, what real data would change, and what follows.

---

*Cross-references to fill in at assembly: Chapter 2 (the Act's provisions; the
literature's evaluation criteria — the claim in §1.1 that compliance is not
among them must be supported there), Chapter 8 (§8.1 the same list).*
