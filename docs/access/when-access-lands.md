# When the real data lands — the day-one procedure

Everything below is built and rehearsed against synthetic exports and the mock
portal. The real dataset or portal should cost a mapping file and nothing else.
This page is the checklist for that first hour.

## 0. Rehearse first (any time, no data needed)

```
python scripts/rehearse_day_one.py
```

Builds a hospital-shaped export from synthetic data — the hospital's own column
names, a column we do not model, an `.xlsx` among the CSVs, day-first dates, a
layer split across two files — runs every step below on it through the real
handling gate, and then searches everything printed and written for one
patient's record number, name and phone. It exits non-zero on a leak. The four
defects it found on 2026-09-18 (a header that means different fields in
different files, a split layer truncated, dates passed through unconverted,
Excel unreadable) are fixed and pinned by `tests/extraction/test_day_one.py`.

On 2026-09-23 a public export we did not generate (the Synthea sample: US-style,
one file per clinical concept, a 28-column registration file) was put through
the same procedure and found three more, now fixed and pinned by
`tests/extraction/test_unseen_export.py`: identifiers read as numbers (`000123`
became `123`, or `123.0` beside a blank, and the patient join failed silently);
a blanked header still counting against a file, so a wide file could never be
read; and an export understood not at all still producing a benchmark and a
headline gap. It also showed the adapter keeping one file per layer and
dropping the rest (conditions, medications and encounters lost behind
allergies). Files with different columns are now stacked.

## A. A dataset (CSV / Excel files)

1. **Put it under `data/`** — e.g. `data/hospital_export/`. Nowhere else: `data/`
   is the only directory the repository ignores.
2. **Write `data/hospital_export/PROVENANCE.md`** before reading anything: who
   supplied it, when, on what basis, and — explicitly — whether and how it is
   de-identified. The adapter refuses to read a real export without this.
3. **Run the check.** It reads headers and row counts only, and it will refuse if
   step 1 or 2 is not done:
   ```
   python scripts/check_source.py data/hospital_export --write-map data/hospital_export/column_map.json
   ```
   The output says, per file, which HIS layer was inferred, which columns were
   recognised, and which were not (`<- map these`). The template it writes has
   every unrecognised header on the left and a blank on the right.
4. **Fill the map.** Right-hand side is a catalogue field name (listed under
   `_catalogue` in the same file). Leave blank to drop a column: a blanked
   column is not read and does not count against the file when its layer is
   judged, and a blank under `"files"` drops a globally mapped header for that
   one file. Each file's `adapter :` line is the adapter's own verdict: `reads
   it as <layer>`, or `NOT READ` and why (too few of its kept columns are
   catalogue fields; only the patient key is recognised, which is on four
   layers). Every value is read as text, so record numbers and phones keep
   their leading zeros. A header that
   means different fields in different files — a patient id that is `mrn` on
   the clinical file and `subject_mrn` on the audit trail — goes under
   `"files"`, per file name; the check prints the exact line to write. Re-run
   the check until the layers are inferred with the confidence you expect.
   Several files for one layer are concatenated when their recognised columns
   agree (an export by month) and stacked when they differ (one file per
   concept: diagnoses, prescriptions, allergies). A stacked row keeps only its
   own file's fields, and a fetch reads only the files carrying a field it asked
   for. Files are not joined on the patient key: a patient has many diagnoses,
   so a join would multiply records or lose them. The pipeline's stage 2 says
   which layers were stacked. Map a date column to `encounter_datetime` only
   where it really is one: every file that carries it is read by a task that
   asks for it. Dates in any common form
   are parsed day-first and emitted in ISO form; values it cannot parse are
   left as written and counted.
5. **Run the pipeline on it:**
   ```
   python scripts/run_pipeline.py --dataset data/hospital_export --column-map data/hospital_export/column_map.json
   ```
   Stages 1–2 report what was understood; stages 3–6 are the same benchmark,
   export audit, purpose matrix and assistant that run on synthetic data. The
   benchmark writes `docs/benchmark_results/benchmark-dataset.{json,md}`. If
   the adapter understood no file, or none of the fields the tasks need, the
   pipeline stops after stage 2 with exit code 2 and writes nothing. The rules
   score an empty pull as compliant, so benchmarking it would report a gap
   measured on no data.
6. **If the structure differs from ours** — a field the catalogue lacks, a layer
   split differently — the one place to change is `src/data_synthetic/catalogue.py`.
   Everything downstream reads it.
7. **Build the page for the room, if wanted:**
   ```
   python tools/build_dataset_page.py data/hospital_export --column-map data/hospital_export/column_map.json
   ```
   Built from a real export, the page shows structure, counts and pseudonyms,
   never values: clinical, financial and quasi-identifying values are replaced
   by their shape. It is written to a git-ignored path, and the builder refuses
   any path git would track. It searches its own output for every identifier the
   export holds before writing. Do not copy it into `docs/review/`; the
   committed copy there is the public Synthea build.

## B. A portal (credentialed URL)

1. **Confirm the basis for access in writing** (who authorised, which account,
   what for) and keep it with the project records. Credentials go in the
   environment or a git-ignored file, never in code.
2. **Run the check.** It logs in, crawls one list page and one record per module,
   and reports what it inferred:
   ```
   python scripts/check_source.py https://portal.example/ --user U --password P --write-map data/portal_aliases.json
   ```
3. **Fill the aliases** — display label on the left, catalogue field on the right —
   and re-run with `--aliases data/portal_aliases.json` until modules are inferred
   with high confidence.
4. **Run the pipeline against it:**
   ```
   python scripts/run_pipeline.py --portal https://portal.example/ --user U --password P --aliases data/portal_aliases.json
   ```
5. **If the crawler cannot read it** — no `<table>`, pagination without a "Next"
   link, detail links elsewhere — the changes belong in
   `src/extraction/tier2/browser.py` (`read_table`, `iter_table_pages`) and
   nowhere downstream. That is the point of the adapter boundary.

## What must not happen

- Real data anywhere but `data/`.
- Real data committed. `git status` should never show it; `check_source.py`
  verifies git actually ignores the path.
- Running the pipeline before `PROVENANCE.md` exists. The adapter enforces this.
- Editing techniques, rules, benchmark or assistant to make real data fit. If that
  seems necessary, the catalogue or the adapter is the place, and it is worth a
  conversation first.
