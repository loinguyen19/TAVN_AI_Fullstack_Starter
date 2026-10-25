# Deployment Architecture (AWS)

## Two tiers: a serverless path for single files

Currently, deployment is for the common cases of same file size of sample file 29 KB
and take around **2.6 ms** to parse and validate. Not for the future case of scalability
of handling, parsing and validating the zipped file: 500MB and 200+ files

[Future implementation discussed below]

So: **CloudFront + Lambda for the synchronous single-file path, the async pipeline
only when the payload demands it (future case).**

```
                  ┌──────────────┐
  Browser ───────▶│  CloudFront   │──▶ S3 (SPA)
                  └───────┬───────┘
                          │  /api/*
            ┌─────────────┴──────────────┐
            │                            │
      file ≤ ~4.5 MB               file > ~4.5 MB
            │                            │
            ▼                            ▼
   ┌──────────────────┐      ┌────────────────────────┐
   │ Lambda (Mangum)  │      │ presigned S3 → SQS →   │
   │ same FastAPI app │      │ Fargate split + fan-out│
   │ 201 with results │      │ 202 + job_id, polled   │
   └────────┬─────────┘      └───────────┬────────────┘
            └──────────┬─────────────────┘
                       ▼
                   DynamoDB
```

`Mangum` adapts the existing ASGI app to the Lambda event model, so `main.py`,
`services.py`, `parser.py` and all eleven validators deploy unchanged.

### What actually constrains the synchronous path

Not the 29-second timeout — compute is 2.6 ms, so a hundred files would finish in a
quarter of a second. **The binding limit is payload size**, and it is a hard one:

| Limit | Value |
|-------|-------|
| Lambda synchronous invoke payload | 6 MB |
| Binary in a Lambda proxy event | base64-encoded, **x1.33 inflation** |
| **Effective file ceiling** | **~4.5 MB** |
| API Gateway REST payload | 10 MB — but the 6 MB Lambda limit binds first |

4.5 MB is roughly 158 sample files, or about 21,700 address entries in one request.
Ample for the single-document case, and 111x short of a 500 MB ZIP. The threshold is
a client-side check on `file.size`: under it, POST directly; over it, request a
presigned URL.

### The consequence people miss: SQLite has to go first

Lambda has an ephemeral filesystem and no shared state between invocations, so
`SqliteReportRepository` cannot follow. This is not optional — it is the first thing
to change, before any Lambda work begins.

**DynamoDB rather than RDS**, specifically because of Lambda. Hundreds of concurrent
Lambda executions each opening a Postgres connection exhausts the pool; avoiding it
means RDS Proxy, which is another component to run and pay for. DynamoDB has no
connection model and suits an insert-only, read-by-id access pattern exactly.

This is where the repository Protocol earns its place: add `DynamoReportRepository`,
change one line in `dependencies.py`, and the service, router and validators are
untouched.

### Cold starts are the real cost

2.6 ms of work behind a 1–3 s cold start is an unflattering ratio. FastAPI and
pydantic are not cheap to import. Options, in order of preference:

1. **Accept it** — for an internal data quality tool with intermittent use, a
   first-request delay is tolerable and costs nothing.
2. **SnapStart for Python** — snapshots the initialised runtime; largely removes
   import cost with no idle charge.
3. **Provisioned concurrency** — eliminates cold starts entirely, but bills for idle
   capacity and so forfeits the main reason to choose Lambda.

### When *not* to split

Two tiers means two runtimes, two deployment artifacts, two sets of IAM policies and
two observability configurations — for one codebase. That overhead is real and it is
permanent.

If traffic is steady rather than spiky, a **single Fargate service behind an ALB
serving both paths** is simpler: one image, one pipeline, workers running the same
container with a different entrypoint. It costs roughly $25–45/month idle (ALB plus a
small always-on task) where Lambda would cost near zero.

So the decision is driven by **traffic shape and cost, not capability**:

| Situation | Choose |
|-----------|--------|
| Spiky or low volume, cost-sensitive | Lambda sync + async pipeline for large files |
| Steady traffic, small team | One Fargate service serving both paths |
| Large files only | The async pipeline alone; no sync path needed |

For a workshop data quality tool — used in bursts when new specification data
arrives, idle overnight — the Lambda split is the better fit.

---
## Future Scenario:

How I would run this in production, and specifically how I would handle the two
problems the brief raises: a 500 MB ZIP containing 200+ files, and the API Gateway
29-second integration timeout.

The short answer to both is the same: **the large payload never travels through the
API, and no HTTP request ever waits for validation to finish.**

---

## 1. Why the obvious design fails

Taking the current synchronous `POST /api/reports` and putting it behind API Gateway
breaks in three independent ways:

| Limit | Value | Consequence |
|-------|-------|-------------|
| API Gateway payload size | 10 MB (REST and HTTP APIs) | A 500 MB upload is rejected outright. Not tunable. |
| API Gateway integration timeout | 29 s default | 200 files cannot be parsed and validated inside one request. |
| Lambda `/tmp` | 512 MB default (10 GB configurable) | A 500 MB ZIP plus its expansion will not fit comfortably. |

So the payload path and the compute path both have to change. Neither is a tuning
problem; they are design problems.

---

## 2. Target architecture

```
                    ┌──────────────┐
  Browser ─────────▶│  CloudFront  │──▶ S3 (React SPA, static)
      │             └──────────────┘
      │
      │ 1. POST /jobs  (small JSON: filename, size)
      │    ◀── 202 { job_id, presigned_url }
      │
      │ 2. PUT file ─────────────────────▶ ┌─────────────┐
      │    (direct to S3, bypasses API)    │  S3 uploads │
      │                                    └──────┬──────┘
      │                                           │ ObjectCreated
      │                                           ▼
      │                                    ┌─────────────┐
      │                                    │  SQS split  │
      │                                    └──────┬──────┘
      │                                           ▼
      │                               ┌───────────────────────┐
      │                               │ Splitter (Fargate)    │
      │                               │ streams ZIP via S3    │
      │                               │ ranged GETs, writes   │
      │                               │ each XML back to S3,  │
      │                               │ enqueues one msg/file │
      │                               └───────────┬───────────┘
      │                                           ▼
      │                                    ┌─────────────┐
      │                                    │ SQS validate│──▶ DLQ
      │                                    └──────┬──────┘
      │                                           ▼
      │                            ┌──────────────────────────┐
      │                            │ Validator workers        │
      │                            │ (Fargate, autoscaled on  │
      │                            │  queue depth, N parallel)│
      │                            │ parser + validators      │
      │                            │ UNCHANGED from this repo │
      │                            └───────┬──────────┬───────┘
      │                                    ▼          ▼
      │                            S3 (results)   DynamoDB (job state,
      │                                            atomic counters)
      │ 3. GET /jobs/{id}  ◀── progress / results
      ▼
┌──────────────┐
│ ALB → ECS    │  FastAPI, same code, no 29 s ceiling
│   Fargate    │
└──────────────┘
```

---

## 3. Answering the brief directly

### "What happens when a user uploads a 500 MB ZIP with 200+ files?"

**The upload never touches the API.** The browser calls `POST /jobs` with a few
hundred bytes of metadata and gets back a **presigned S3 URL**. It then `PUT`s the
file straight to S3. API Gateway's 10 MB limit is irrelevant because the bytes never
cross it, and the API tier does no I/O proportional to file size.

For 500 MB I would use **multipart upload** rather than a single PUT: the browser
requests presigned URLs per part, uploads parts in parallel, and retries only the
failed part. On a flaky connection a single 500 MB PUT that dies at 98% has to start
over.

Presigned URLs are scoped tightly — one key, 15-minute expiry, and a
`content-length-range` condition so the URL cannot be used to upload something far
larger than declared.

**The ZIP is then streamed, not loaded.** An S3 `ObjectCreated` event enqueues a
split job. A splitter task reads the archive using **S3 ranged GETs behind a seekable
file-like object**, so Python's `zipfile` can work over it without ever holding
500 MB in memory.

This detail matters and is easy to get wrong: a ZIP's central directory lives at the
*end* of the file, so you cannot process one as a forward-only stream. The reader
fetches the EOCD record, then the central directory, then each entry by byte range.
Peak memory stays proportional to the largest single entry, not the archive.

Each extracted XML is written back to S3 and one SQS message per file is enqueued.
200 files become 200 independent units of work.

**Then it fans out.** Validator workers consume the queue in parallel, running the
*unchanged* `parser.py` and `validators/` from this repo. Each writes its result to
S3 and atomically increments a counter in DynamoDB. When processed equals expected,
the job flips to `complete`.

With 20 workers, 200 files finish in roughly the time of 10 sequential files.

### "How do you handle the API Gateway 29-second timeout?"

**Nothing waits.** `POST /jobs` returns `202 Accepted` with a `job_id` in
milliseconds — it writes a DynamoDB row and mints a presigned URL, nothing more.

Progress is reported by polling `GET /jobs/{id}`:

```jsonc
{ "job_id": "...", "status": "processing",
  "files_total": 200, "files_done": 143, "files_failed": 2,
  "summary": { "error": 31, "warning": 88, "info": 204 } }
```

Each of those calls is a single-digit-millisecond DynamoDB read. The client polls
every 2 s, or subscribes to Server-Sent Events / API Gateway WebSockets for push
updates on long jobs.

**I would also sidestep the limit structurally** by putting the API behind an
**ALB + ECS Fargate** rather than API Gateway. An ALB has no 29-second cap (idle
timeout is configurable to 4000 s), and it runs the existing FastAPI app unmodified.
API Gateway earns its place when you need usage plans, API keys, WAF or per-route
authorizers — and if it is mandated, it only ever fronts the fast job-control
endpoints, never the processing path.

Worth noting: AWS now allows requesting an increase above 29 s for regional REST
APIs. I would not rely on it. A design that needs a raised timeout will eventually
meet a file that exceeds the new one too.

---

## 4. Components

| Concern | Choice | Why |
|---------|--------|-----|
| SPA hosting | CloudFront + S3 | Static build, cached at edge, no servers |
| API | ALB + ECS Fargate | Runs this FastAPI app as-is; no 29 s ceiling |
| Object storage | S3 (SSE-KMS) | Uploads, extracted XML, result JSON |
| Queues | SQS (+ DLQ each) | Decouples ingest from compute, absorbs bursts |
| Workers | ECS Fargate, autoscaled | Long-running, no 15-min Lambda cap, no cold starts |
| Job state | DynamoDB | Atomic counters, TTL expiry, single-digit-ms reads |
| Upload history | RDS Postgres | Replaces SQLite; needs concurrent writers |
| Secrets | Secrets Manager | DB credentials, rotated |
| Observability | CloudWatch + X-Ray | Metrics, structured logs, traces |

**Why Fargate over Lambda for workers.** Lambda is attractive for the fan-out, and
for the per-file validators it would work. The splitter is the problem: a 500 MB
archive against a 15-minute ceiling and constrained `/tmp` is uncomfortably close to
the edge, and the failure mode is a timeout partway through a job. Fargate removes
the cliff. I would reconsider Lambda for the per-file stage once throughput data
exists — the validators are pure functions and port cleanly.

---

## 5. Failure modes

The one that matters most: **one bad file must not fail a 200-file job.**

- **Poison messages** — SQS redrive to a DLQ after 3 attempts. The file is recorded
  as `failed` with its error; the job completes with a per-file status breakdown.
- **Idempotency** — SQS is at-least-once, so the same file can be delivered twice.
  Results are keyed on `(job_id, file_key)` and written idempotently; a redelivery
  overwrites rather than double-counting.
- **Zip bombs** — reject entries whose uncompressed-to-compressed ratio exceeds a
  threshold, cap total uncompressed size, and cap entry count before extracting.
- **Path traversal** — ZIP entry names are attacker-controlled. Reject any containing
  `..` or an absolute path; never join them onto a filesystem path unsanitised.
- **Partial progress** — the job row always reflects reality, so a client that
  disconnects can reattach with the `job_id` and see where things stand.
- **Stuck jobs** — a sweeper marks jobs with no counter movement past a deadline as
  `stalled` rather than leaving them `processing` forever.

## 6. Scaling and cost

Workers autoscale on **queue depth per task** (target tracking on
`ApproximateNumberOfMessagesVisible`), which tracks actual backlog far better than
CPU. Scale to zero between jobs; this workload is bursty.

Cost is dominated by Fargate task-seconds, so the levers are worker efficiency and
scale-to-zero, not instance choice. S3 lifecycle rules expire extracted XML after a
few days and transition result JSON to Infrequent Access; DynamoDB TTL expires job
rows. Idle cost approaches the ALB hourly charge plus RDS.

Per-tenant S3 prefixes and a tenant id on every job row keep isolation and cost
attribution straightforward.

## 7. Security

- S3 buckets private; all access presigned or via IAM role. Block Public Access on.
- Presigned URLs: single key, short TTL, `content-length-range` condition.
- Least-privilege task roles — the splitter cannot read the results bucket, the
  validators cannot write to the uploads bucket.
- Encryption at rest (SSE-KMS) and in transit throughout.
- Workers in private subnets, egress via NAT or VPC endpoints; no inbound.
- WAF on CloudFront for rate limiting and common exploit rules.

## 8. What changes in this repo

The validator design holds up well under this migration, which is the main payoff of
keeping detection pure:

| File | Change |
|------|--------|
| `validators/*` | **None.** Pure functions over a parsed document. |
| `parser.py` | **None.** Already takes bytes. |
| `repository.py` | Add a DynamoDB (Lambda path) or RDS (Fargate path) implementation of `ReportRepository`. The only module that must change — the protocol keeps the service and router untouched. |
| `services.py` | Largely reusable; add a job-oriented entrypoint alongside the synchronous one. |
| `main.py` | Split: API routes (job control) and a worker entrypoint (SQS consumer). |
| *(new)* | `zip_splitter.py` — S3-ranged-GET seekable reader and fan-out. |

A sensible path there: lift and shift to Fargate behind an ALB with RDS first
(small change, no behaviour difference), then add the async job pipeline once
multi-file upload is actually needed. The single-file synchronous endpoint can stay
indefinitely for small files — it is a better experience than polling when a file
takes 200 ms.
