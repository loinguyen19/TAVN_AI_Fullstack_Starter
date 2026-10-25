# Torque Specification Validator

Parses automotive torque specification XML files and reports data quality issues.
Python/FastAPI backend + React/TypeScript frontend, orchestrated with Docker Compose.

## Prerequisites

- Docker Desktop (tested with Docker 28.5.1 / Compose v2.35.1)
- Ports `3000` and `8000` free

No local Python or Node install is required — both run in containers.

## Quick start

```bash
docker compose up --build
```

First run takes a minute or two (pip install + npm install). Then:

| Service  | URL                           |
|----------|-------------------------------|
| Frontend | http://localhost:3000         |
| Backend  | http://localhost:8000         |
| API docs | http://localhost:8000/docs    |

Both services run in hot-reload mode: the backend uses `uvicorn --reload` and the
frontend uses the Vite dev server, and the source directories are bind-mounted, so
edits on the host apply without a rebuild.

Stop with `Ctrl+C`, or `docker compose down` to remove the containers.
Note: Please keep in mind that for current implementation, SQLite only perists past uploads
by running on docker container. Running without docker will not persist past uploads.

## Verify it works

Open http://localhost:3000 and upload `data/AZD-AZD-AZDMUC4161-F01_RBU.xml`.

Expected result: **137** entries and **20** findings — 5 errors, 5 warnings, 10 info.

```bash
curl -s -F file=@data/AZD-AZD-AZDMUC4161-F01_RBU.xml \
  http://localhost:8000/api/reports | jq '.summary'
```

## Findings in the sample file

Every finding below is produced by a deterministic rule (a regex plus a lookup table). 
The *why* column is the reason the rule exists.

### Errors — the entry is unusable or dangerous

| Code | Value | Issue | Why it matters |
|------|-------|-------|----------------|
| `111AZ` | `8500` | Torque beyond any workshop tool (>1000 Nm) | Subframe-to-body M12. The sibling entry `112AZ` (same joint, rear) reads `150,0`. The likely cause is a lost decimal separator — `85,00` written as `8500` — a 100x error on a structural chassis fastener. |
| `90AZ` | `-8,5` | Negative torque | A specification is a magnitude; a wrench cannot be set to -8,5. On a brake caliper guide pin. |
| `103AZ` | *(none)* | No torque value | A suspension mount with no spec at all; the fastener gets tightened by feel. |
| `87AZ` | `18,5` / `22,0` | Overlapping validity, conflicting values | Brake booster. Valid 2008-2025 at 18,5 Nm *and* 2022-2030 at 22,0 Nm — any lookup in 2022-2025 returns two different answers. |
| `126AZ` | `10,0` / `8,0` | Overlapping validity, conflicting values | Same defect, window regulator, ambiguous across 2014-2015. |

### Warnings — likely wrong, needs a human decision

| Code | Value | Issue | Why it matters |
|------|-------|-------|----------------|
| `80AZ` | `350,0` | Above the plausible band for M12 (35-200 Nm) | Crankshaft main bearing cap. An M12 10.9 bolt calculates to ~133 Nm; 350 Nm shears it. |
| `116AZ` | `45,0` | Below the plausible band for M16 (85-500 Nm) | Steering wheel to column. An under-torqued steering fastener can work loose. |
| `111AZ` | `8500` | Only value of 136 not written as `d,d` | Corroborates the dropped-separator reading above, by a completely independent rule. |
| `126AZ` | — | Notes say "from 07/2015", `StartDate` is `2014-01-01` | The prose and the date field disagree; neither is obviously authoritative. |
| `81AZ` | `24,0` | "step 1" with no step 2 in the file | A staged torque-then-angle procedure published half-finished; the technician stops at 24 Nm on a connecting rod cap. |

### Info — advisories a reviewer should see

| Codes | Issue |
|-------|-------|
| `3AZ`, `61AZ`, `77AZ`, `126AZ` | Expired before the document date — confirm the superseding entry exists |
| `10AZ` | Left-hand thread |
| `97AZ` | Single-use nut, replace after each removal |
| `103AZ` | Thread-locking compound required |
| `130AZ` | Anti-seize required (which also changes the friction the torque assumes) |
| `53AZ` | Procedural tightening: hand-tight, then 1/2 turn |
| `80AZ` | Must be tightened in sequence |

### How the non-obvious rules work

**Thread-size bands** (`torque_plausibility.py`). The band table is derived, not
guessed: `T = K * 0.7 * A_s * R_p0.2 * d` with K=0.2, giving reference values of
M12 ≈ 133 Nm and M16 ≈ 331 Nm at property class 10.9. Since the data almost never
states a class, bands span 8.8 through 12.9 plus friction variation (ceiling ≈1.5x
the 10.9 reference). 15 entries state a thread size; the bands flag 3 and clear 12.

A plain statistical outlier test was tried first and rejected: an IQR fence lands at
110 Nm and flags 11 entries, 9 of them legitimate (wheel bolts, axle nut, control arms).

**Notes/date convention** (`notes_date_consistency.py`). The rule was derived from the
data, not assumed: 7 notes use the `from|to MM/YYYY` form and **6 conform exactly** to
the matching date field. That ratio is what makes the 7th a defect rather than noise.

## API

| Method | Path                              | Description                                       |
|--------|-----------------------------------|---------------------------------------------------|
| POST   | `/api/reports`                    | Validate an `.xml` document, store the report (201)|
| GET    | `/api/reports`                    | Past reports, newest first (`?limit=`)             |
| GET    | `/api/reports/{id}`               | One stored report, same shape as the 201 response  |
| GET    | `/api/reports/{id}/export.csv`    | Findings as CSV (Excel-safe UTF-8 BOM)             |
| GET    | `/api/validators`                 | Registered validators and their rationales         |

The resource is a **report** — a document plus its findings plus a timestamp —
rather than an "upload", which reads as both a verb and a noun.

Non-`.xml` filenames and malformed XML return HTTP 400. A *readable* file with a bad
field value returns 200 with a finding — a single unparseable torque must never fail
the whole upload, or the validator meant to report it never runs.

Upload history is stored in SQLite (stdlib `sqlite3`, no extra dependency) on a named
Docker volume, so it survives `docker compose down`.

## Running without Docker

Backend:

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

**Caveat:** `frontend/vite.config.ts` proxies `/api` to `http://backend:8000` — the
Docker Compose service name, which does not resolve outside Docker. To run the
frontend on the host, temporarily change that target to `http://localhost:8000`.
NOTE: Do not encourage to run withou Docker, no SQLite spin up.

## Project layout

```
backend/
  app/
    main.py                        HTTP layer: routing and status codes only
    services.py                    Orchestration + CSV building; no web, no SQL
    repository.py                  ReportRepository protocol + SQLite impl
    dependencies.py                FastAPI Depends wiring (IoC)
    parser.py                      XML -> TorqueDocument/Address
    validators/
      base.py                      BaseValidator, ValidationResult, Severity
      registry.py                  VALIDATORS list + fault-isolated runner
      missing_torque.py            absent torque value
      torque_value.py              non-positive / unparseable
      torque_plausibility.py       thread-size bands + absolute ceiling
      decimal_format.py            notation inconsistent with the file
      validity_overlap.py          overlapping validity periods per code
      notes_date_consistency.py    notes period vs date fields
      date_sanity.py               ISO format, ordering, expiry
      required_fields.py           missing Code/Notes/dates
      incomplete_procedure.py      "step 1" with no step 2
      special_handling.py          left-hand thread, single-use, thread lock...
      document_metadata.py         filename vs document metadata
frontend/
  src/
    App.tsx                        Upload, history wiring, layout
    types.ts                       API response types
    components/
      SummaryBar.tsx               Severity counts as filter chips
      ValidationPanel.tsx          Findings: filter, search, group-by
      DataTable.tsx                Extracted data with severity dots
      HistoryPanel.tsx             Past uploads, view + per-row CSV
      ExportButton.tsx             CSV download
      SeverityBadge.tsx            Severity pill
data/
  AZD-AZD-AZDMUC4161-F01_RBU.xml   Sample file
```

## UI

- **Severity chips** at the top double as filters — click to show/hide a level.
- **Findings table** supports a validator dropdown, free-text search over code and
  message, and a group-by toggle (none / code / validator). Grouping by validator
  shows each rationale once in the group header rather than on every row.
- **Clicking a finding** scrolls to and highlights the matching row in the data table.
- **Data rows** carry a coloured dot showing their worst severity.
- **Upload history** lists past runs with their counts; view one to reload it, or
  download its CSV directly.

## Tests

```bash
docker compose exec backend python -m pytest
```

88 tests covering the parser, the service layer, every validator (a passing *and* a failing case each),
and every endpoint including the 400/404 paths. A golden test pins the exact findings
on the sample file — 20 results at 5 error / 5 warning / 10 info, with the precise
codes each validator reports — so any regression fails loudly rather than silently
changing the numbers in this README.

## Adding a validator

1. Create a file in `backend/app/validators/`
2. Subclass `BaseValidator`, implement `name` and `validate()`
3. Set `rationale` — one sentence on why this class of issue matters in a workshop
4. Register the class in `backend/app/validators/registry.py`
5. Add a test to `backend/tests/test_validators.py` — one case that fires, one that
   does not — and extend `EXPECTED_BY_VALIDATOR` in the golden test

Each validator covers one *class* of issue. `message` is per-row and specific;
`rationale` is per-class and is returned once in the response's `validators` map
rather than repeated on every finding. `run_all_validators` isolates failures: a
validator that raises is reported as a finding against itself instead of failing
the upload.

## Design notes

- **The parser never raises on a bad field.** `torque_raw` keeps the original string
  alongside the parsed float, because `float()` erases the evidence — `8500`,
  `8500,0` and `8500.00` all become `8500.0`, and only the raw text reveals a lost
  separator. It also distinguishes "no Torque element" from "Torque we could not read".
- **Layered, with the seam at the repository.** `main.py` does HTTP,
  `services.py` does orchestration and knows nothing about FastAPI (it raises
  domain errors the router maps to status codes), `repository.py` does
  persistence behind a `typing.Protocol`. Wiring is FastAPI `Depends` rather
  than a DI container — it is the idiomatic IoC mechanism here, and tests swap
  the repository with `app.dependency_overrides`. Swapping SQLite for RDS means
  adding one class in `repository.py` and touching nothing above it.
- **Severity means something.** ERROR = unusable or dangerous as published.
  WARNING = likely wrong, needs a human. INFO = correct but worth knowing.
  Heuristics (the thread-size bands) only ever produce WARNING.

## Open Topic: documentation

| File | Contents |
|------|----------|
| `ARCHITECTURE.md` | AWS deployment: presigned S3 upload for 500 MB ZIPs, SQS fan-out for 200+ files, async jobs for the API Gateway 29 s timeout |
