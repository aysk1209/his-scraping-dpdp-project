# Chapter 5 — Acquisition: portal, browser, dataset

*Draft 1, 2026-09-15. Target ~1600 words; this draft runs ~2100. §5.4 carries
the real-data slot. No section of the Act is cited here; the handling gate of
§5.3 rests on the accountability principle established in §3.3.7.*

---

Chapters 3 and 4 treat the data source as given. This chapter is about getting
data out of a system in the first place, and its argument is that the
*structure* of a hospital information system can be **discovered rather than
declared**, and **classified from content rather than from labels**. That is our
answer to the doubt that hospital systems are too heterogeneous for one method
to transfer: we do not tell the crawler what a module is; it works it out from
the fields it finds, and the same classification reads a spreadsheet the
hospital exports. Three components make the argument: a portal fixture built to
behave like a system we do not control (§5.1), a browser-driven extraction layer
that discovers and reads it (§5.2), and a file-based adapter with a handling gate
for the real export (§5.3). §5.4 describes the synthetic data that stands in for
the real structure until it is seen.

## 5.1 A portal we do not control

We have credentialed access to a hospital system on paper and have not been
able to use it. Rather than build against a system we cannot reach, we built a
**test fixture**: a small, server-rendered, login-gated web portal that serves
records from any `HISDataSource` as HTML, and we scrape it with a real browser.
It is not a simulation of a hospital system and does not try to be. It exists to
exercise the browser layer for real and to make techniques cost different
amounts.

The fixture was built on one rule the team set before writing it: **assume we do
not control it.** The scraper holds a username and a password and nothing else.
So the portal offers exactly what a third party's system would offer and no
more:

- a login form with a per-session token and a session cookie, redirecting
  anything unauthenticated back to the login page;
- server-rendered HTML tables, paginated, with a search box;
- a record page per row showing fields the list page does not;
- a `robots.txt` that disallows everything, as a credentialed portal would.

And it withholds everything a scraper would find convenient: no JSON endpoint,
no data attributes, no stable identifiers in the markup, no API. Its module
paths use portal vocabulary — `/m/registration/`, `/m/billing/` — not our layer
names, so nothing about the URL tells the crawler what it is looking at. Which
fields appear on the list page and which only on the record page follows what a
portal would plausibly show in a table (a name and a ward, but not an address),
not what would flatter the benchmark. If the extraction layer can read this
portal, it is because it does what it would have to do against a real one.

The fixture serves whatever source it is given. Today that is the synthetic
generator; when the hospital dataset arrives, the same portal serves it
unchanged through the dataset adapter of §5.3, and the browser layer is then
exercised against real structure without any change to the fixture. Records are
read once at start-up and held in memory, so pagination over a large export is
cheap; a run with five thousand records per module produces several hundred
pages per module.

**Limitation, stated.** A portal we wrote cannot surprise us the way a vendor's
can. It is cleaner than a real system — one table per page, consistent headers,
no JavaScript, no frames, no session timeouts. It demonstrates the *mechanism*
of browser-driven extraction and produces honest cost differences between
techniques; it does not demonstrate robustness against real interfaces, and we
do not claim that it does. The label mode of §5.2 is the one deliberate step
toward realism, and the hospital dataset narrows the gap on the data side; only
live access closes it.

## 5.2 Browser-driven extraction

Our extraction sits at what our first review called Tier 2 — credentialed,
browser-automated access — and the machinery (`src/extraction/tier2/`) is
everything a scraper has to do when it holds a login and nothing else.

**The session.** A real browser, driven headless, submits the login form; the
browser carries the hidden token and the cookie as a browser does. Tables are
read as a reader would read them — header cells for names, body cells for
values, the link in the last column to open a record. Pages are turned by
following the "Next" link until there is none. Every page the browser loads is
counted, because that is the cost. Nothing in the session knows the portal is
ours: it uses generic selectors — `table`, `thead th`, `tbody tr`, `a` — and
visible text, never identifiers or data attributes, so it transfers to a real
portal as a change of selectors and credentials rather than of approach.

**Discovery.** From the home page after login, the crawler follows every link
it finds to a module, reads the first list page and the first record page, and
builds a **navigation map**: for each module, its title and path, how many pages
and records it has, which fields appear in the list table and which only on the
record page. On the fixture this takes eleven page loads. The map is written as
an artefact (`navigation-map.{json,md}`; Table 4 of Chapter 7) and is what every
downstream component uses to know where things are — including the staff
assistant, whose instruction steps are placed on the pages the crawler found.

**Layer inference from field names.** This is the heterogeneity answer as code.
The crawler does not read the URL, the module title, or any label to decide
which of the five HIS layers a module belongs to. It takes the set of field
names it found on the module's pages and asks which layer's catalogue explains
the most of them (`infer_layer` in the field catalogue). A module at
`/m/registration/` whose pages carry `mrn`, `full_name`, `date_of_birth` and
`admission_ward` is classified as Patient Administration because those are
Patient Administration fields; the path is never consulted. The classification
carries a confidence — the share of the fields seen that the inferred layer's
catalogue explains — so a module the catalogue does not describe is reported as
unclassified rather than guessed at. On the fixture every module classifies at
100%, because the fixture's headers are catalogue names; that is the limitation
the next paragraph addresses.

**The label map: the one piece of portal-specific knowledge.** A real portal
shows display labels — "Patient ID", "DOB", "Ward" — not catalogue names. The
fixture renders labels on request so this can be tested, and the adapter takes a
`field_aliases` map from label to catalogue field, applied as headers are read;
matching ignores case and spacing, and unmapped headers pass through unchanged.
The result (Chapter 7, §7.4) is the transfer property in two halves: without the
map, the labelled module cannot be classified — "Patient ID" is an unknown
column and confidence falls below one half; with it, the same portal is
understood at 100% and discovery, layer inference, fetching, the three
techniques and the benchmark all run unchanged. The map is data, not code, and
it lives in the adapter, which is the one place in the chain that is allowed to
know anything about a particular portal.

**Cost is real here.** The adapter reads a field from the list table when it is
a list column and opens a record page only when a requested field lives there
alone. A technique that asks for more than it needs therefore loads more pages,
and the meter of Chapter 4 reports the browser's own count. This is where the
benchmark's page-load column comes from, and it is not simulated.

The three techniques were written against the in-memory source and run against
this adapter **unchanged**; the test suite asserts it. That is the proof the
adapter boundary of Chapter 4 holds, and it is what makes the next component a
configuration step rather than new code.

## 5.3 The dataset adapter and the handling gate

A hospital's own export is the most likely form in which real data reaches us:
a directory of tabular files, CSV or spreadsheet, one per module or one per
layer, with the hospital's column names. `DatasetHISDataSource` reads such a
directory through the same interface, and nothing in it depends on the files
being ours.

**Classification by content.** Each file is classified by its *columns*, using
the same `infer_layer` the crawler applies to a portal module — so a spreadsheet
and a web page are understood the same way, and a file called
`PatientMaster_2026.csv` is classified as Patient Administration because of what
is in it, not what it is called. A file no layer explains above the confidence
threshold is reported as unclassified; if two files map to one layer, the
better-explained one is kept.

**The column map.** Headers are whatever the hospital called them. A
`column_map` renames export headers to catalogue fields (`{"Patient ID": "mrn"}`)
before classification; columns that already match the catalogue are kept as
they are; and anything else is **dropped and reported, never silently carried
through** — a column the catalogue cannot categorise is a column the rules
cannot score, and it must not reach them unlabelled. The real export is, in the
end, that map. A day-one diagnostic (`scripts/check_source.py`) reads a
directory, reports what was understood, and writes the mapping template for the
team to complete.

**The handling gate — why a compliance project must gate its own inputs.** A
hospital export is, in all likelihood, real personal data of real patients. A
project whose entire contribution is data-protection compliance cannot be
careless with it; being non-compliant with the Act we benchmark against would be
a serious and highly visible failure. We therefore do not rely on anyone
remembering the handling rules. `compliance/handling.py` enforces them: unless a
directory is a synthetic export (its manifest says so), the adapter refuses to
read it until four things are true —

1. it lives under `data/`, the directory the repository ignores;
2. git actually reports it as ignored — the rule is in force, not merely
   intended;
3. a `PROVENANCE.md` sits beside it, stating who supplied it and on what basis;
4. that note states the de-identification status.

The gate is applied in the adapter's constructor, so there is no path through the
pipeline that reads real data without it. The provenance note is also the record
by which we can later demonstrate how the data was obtained and handled — the
accountability principle applied to ourselves. The de-identification question
is to be settled *before* the data arrives, not after; the gate makes "after"
impossible to overlook.

## 5.4 Synthetic data, and the real-data slot

Until a real structure is seen, a synthetic one stands in for it, and the team's
decision was to build the whole pipeline against the synthetic structure rather
than wait. Three components make that safe.

**The catalogue.** One table (`data_synthetic/catalogue.py`) lists every field
by HIS layer with its DPDP category. It is the single source that the generator,
the per-layer schemas, the interoperability shaping, the crawler's layer
inference and the dataset adapter's classification all read. If the real
structure differs, the catalogue is the one place to change.

**The generator and schemas.** A generator produces records per layer from the
catalogue, seeded for reproducibility; one validating schema per layer is
*derived* from the catalogue so that the two cannot disagree about which fields
a layer has. Types are deliberately permissive where a real export might be
messy — dates as ISO strings, amounts as floats — so that a real file validates
on structure without a normalisation pass first. A synthetic export writer
produces one file per layer plus a manifest into `data/`, which is how the
dataset adapter was built and tested against files of the right shape before
any real file existed.

**The fifth layer as audit events.** The Infrastructure / Integration layer is
modelled as a record set of audit events — event identifier, timestamp, actor
role, action, source system, and the medical record number of the subject. It is
compliance instrumentation, not a patient record, and it is not identifier-free:
an audit event names the record it concerns. That is why it is in the catalogue
as personal data, why it shapes to a FHIR `AuditEvent`, and why that artefact is
granted to no staff role (Chapter 6).

**[real data] The hospital export.** *To be written when it arrives:*

- *Structure: files, columns, and the column map that was needed.*
- *What the adapter understood: the layer each file classified into and at what
  confidence; columns dropped as unrecognised, and what they were.*
- *What differed from the catalogue — fields the hospital has that we did not
  model, and fields we modelled that it does not carry — and what was changed
  in the catalogue in consequence.*
- *Whether the export was also served through the portal fixture, and what the
  crawler made of it.*

---

*Cross-references to fill in at assembly: Chapter 3 (§3.2 the catalogue and
categories; §3.3.7 accountability), Chapter 4 (§4.1 the adapter boundary; §4.3
page loads as cost), Chapter 6 (`AuditEvent`; the assistant's pages), Chapter 7
(§7.4 Table 4 and the label-mode result; §7.7 real data; §7.8 the fixture
limitation).*
