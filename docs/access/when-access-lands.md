# When the real data lands — the day-one procedure

Everything below is built and rehearsed against synthetic exports and the mock
portal. The real dataset or portal should cost a mapping file and nothing else.
This page is the checklist for that first hour.

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
   `_catalogue` in the same file). Leave blank to drop a column. Re-run the check
   until the layers are inferred with the confidence you expect.
5. **Run the pipeline on it:**
   ```
   python scripts/run_pipeline.py --dataset data/hospital_export --column-map data/hospital_export/column_map.json
   ```
   Stages 1–2 report what was understood; stages 3–6 are the same benchmark,
   export audit, purpose matrix and assistant that run on synthetic data. The
   benchmark writes `docs/benchmark_results/benchmark-dataset.{json,md}`.
6. **If the structure differs from ours** — a field the catalogue lacks, a layer
   split differently — the one place to change is `src/data_synthetic/catalogue.py`.
   Everything downstream reads it.

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
