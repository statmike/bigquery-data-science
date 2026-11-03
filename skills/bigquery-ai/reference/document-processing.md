# Document Processing & Unstructured Data (Object Tables / ObjectRef) in BigQuery

Contents: [Options](#options) · [Choosing among them](#choosing-among-them) · [Gotchas verified in this repo](#gotchas-verified-in-this-repo) · [Canonical snippet](#canonical-snippet) · [Go deeper](#go-deeper)

> `ML.PROCESS_DOCUMENT` is one of **five** functions that reach a pre-trained Cloud AI service through a `REMOTE_SERVICE_TYPE` remote model — the others are `ML.TRANSLATE`, `ML.UNDERSTAND_TEXT`, `ML.ANNOTATE_IMAGE`, and `ML.TRANSCRIBE`. Everything they share (the handle-not-a-model create, no `ML.EVALUATE`, per-row `*_status` failures, the per-service IAM matrix) is in [`cloud-ai-service-models.md`](cloud-ai-service-models.md). This page carries the Document AI specifics.

## Options

| Capability | What it does | Use this when |
|---|---|---|
| `AI.CHUNK_DOCUMENT` (GA) | Table-valued function that splits PDF, HTML, DOCX, PPTX, and XLSX/XLSM documents in Cloud Storage (via `'gs://...'` URI/wildcard, `TABLE object_table`, or `(SELECT ... AS ref)` subquery) into layout-aware chunks (`chunk_size` in `[1, 2000]` tokens, default `1000`), returning `chunk_id`, `start_page`, `end_page`, `content` (prefixed with ancestor section headings), and `status` plus passthrough columns. | You need layout-aware document chunking with 1-indexed PDF page provenance (`start_page`, `end_page`) for RAG or embedding pipelines (`AI.EMBED` + `VECTOR_SEARCH`) with **zero `CREATE MODEL` and zero manual Document AI processor provisioning**. |
| `ML.PROCESS_DOCUMENT` | Table-valued function that sends documents from an object table to a Document AI processor (invoice, receipt, form, OCR, custom, and more) via a `REMOTE_SERVICE_TYPE = 'CLOUD_AI_DOCUMENT_V1'` remote model, returning structured extraction results as columns. | You need specialized document extraction (invoices, receipts, forms, tax/ID documents, custom classifiers/splitters) at scale, and can create a Document AI processor + remote model. |
| `AI.PARSE_DOCUMENT` | **RETIRED / OFFLINE (since 2026-06-01; reference docs withdrawn 404) — does not execute.** Superseded by `AI.CHUNK_DOCUMENT` (for zero-DDL layout-aware RAG chunking) and `ML.PROCESS_DOCUMENT` (for specialized Document AI processor extraction). | Historical archive only — never recommend for new queries. Route RAG chunking to `AI.CHUNK_DOCUMENT` and invoice/form extraction to `ML.PROCESS_DOCUMENT`. |
| Object Tables | Read-only external SQL tables over Cloud Storage objects (PDFs, images, audio, video), exposing metadata columns (`uri`, `content_type`, `size`, etc.) and an optional `ref` (ObjectRef) column. | You want to index/query a whole GCS prefix as rows and feed many objects into AI functions or `ML.PROCESS_DOCUMENT` at scale. |
| `OBJ.MAKE_REF` | Scalar function that builds a partial `ObjectRef` STRUCT (`uri` + `authorizer`) from a URI string and a connection — no object table required. | You need a one-off reference to a single (or small UNNEST list of) GCS file(s) without registering a whole Object Table. |
| `OBJ.LIST` (GA 2026-09-30) | Table-valued function: one wildcard path (`gs://bucket/prefix/*.pdf`, optional connection) returns every matching object's metadata plus a ready `ref` `ObjectRef`. An object table's listing with no DDL and no persistence. | You want "every file under this prefix" in an AI call right now — discovery, prototyping, or a load pipeline — and do not need a table that keeps tracking new arrivals. |
| `OBJ.FETCH_METADATA` | Scalar function that fills in the `details` field of a partial `ObjectRef` with GCS metadata (content type, size, MD5 hash, updated time). | You need actual object metadata (size, content-type, hash) attached to an ObjectRef, or need it before generating an access URL. |
| `OBJ.GET_ACCESS_URL` | Scalar function that converts an `ObjectRef` into `ObjectRefRuntime` JSON containing signed read **or** write URLs, with a caller-chosen TTL. Has an `ARRAY<objectref>` overload. | You need a signed URL — to hand an object to something outside BigQuery, to write, or to control the expiry. **Not** required to call an AI function: those take the `ObjectRef` itself. |
| `OBJ.GET_READ_URL` | Scalar function returning `STRUCT<url, status>` — a read-only signed URL on a fixed 45-minute TTL, requiring delegated access. | You want to display an object (a BigQuery Studio image preview, say) and do not need a write URL or a custom TTL. |

## Choosing among them

- **"I need to split PDFs or Office/HTML documents in Cloud Storage into layout-aware chunks with page numbers for RAG (`AI.EMBED` + `VECTOR_SEARCH`)"** → `AI.CHUNK_DOCUMENT`. Pass a `'gs://bucket/prefix/*.pdf'` URI/wildcard literal, `TABLE my_object_table`, or a single-column `(SELECT ref FROM OBJ.LIST(...))` subquery plus `connection_id => 'project.region.conn'` and optional `chunk_size => INT64` (`[1, 2000]` tokens, default `1000`). No `CREATE MODEL` or manual Document AI processor creation is needed.
- **"I need to extract structured fields (invoice line items, receipt totals, form key-value pairs) from PDFs/scanned documents at scale"** → `ML.PROCESS_DOCUMENT` (or `AI.GENERATE` with `output_schema` over `ObjectRef` for ad-hoc extraction without provisioning a processor).
- **"I need to pass images/PDFs/audio/video into `AI.GENERATE` or other generative functions"** → build an `ObjectRef` via an Object Table's `ref` column (bulk, persistent), `OBJ.LIST(path)`'s `ref` column (bulk, ad hoc), or `OBJ.MAKE_REF(uri, connection)` (single file) and pass it **straight to the function**. No `OBJ.GET_ACCESS_URL`, no `EXTERNAL_OBJECT_TRANSFORM`.
- **"I just need a one-off reference to a single GCS file without registering a whole Object Table"** → `OBJ.MAKE_REF`. **"…or every file under a prefix, still without an Object Table"** → `OBJ.LIST`. Measured 2026-10-09: its `ref` feeds `AI.GENERATE`, the typed variants, `AI.IF`/`AI.SCORE`/`AI.CLASSIFY`, `AI.AGG`, `AI.EMBED` and `AI.SIMILARITY` directly, with or without the connection argument (without it, the objects are read as the query runner — fine on a public bucket, needs `storage.objectViewer` otherwise). The path must be a literal with at most one `*` per segment and must not end in `/`; `ML.PROCESS_DOCUMENT` still needs a real object table.
- **"I need metadata (size, content-type, etc.) about a GCS object"** → `OBJ.FETCH_METADATA`.
- **"I need a signed/temporary URL to a GCS object"** → `OBJ.GET_ACCESS_URL` (read or write, your TTL), `OBJ.GET_READ_URL` (read-only, fixed 45 minutes, for display), or `EXTERNAL_OBJECT_TRANSFORM(... ['SIGNED_URL'])` when working from an Object Table. **This is the one genuine use for all three** — it is not a step on the way to an AI function.

## Gotchas verified in this repo

- **`AI.CHUNK_DOCUMENT` verified signature, input forms, and gotchas (GA, measured live 2026-11-02)**:
  - Signature: `AI.CHUNK_DOCUMENT({'gs://...' | TABLE object_table | (SELECT ... AS ref)}, connection_id => '...', [chunk_size => INT64])` returning `chunk_id INT64`, `start_page INT64`, `end_page INT64`, `content STRING`, `status STRING`, plus passthrough columns from the input table/subquery (`uri`, `ref`, etc.).
  - **Passing `OBJ.LIST(...)` directly fails**: `AI.CHUNK_DOCUMENT(OBJ.LIST(...), ...)` fails with `Provided query does not match required schema. Expected a single column of type STRUCT<uri STRING, version STRING, authorizer STRING, details JSON> named ref` because `OBJ.LIST` returns 8 columns. Either pass the `'gs://bucket/prefix/*.pdf'` wildcard string directly as argument 1, or wrap `OBJ.LIST` in `AI.CHUNK_DOCUMENT((SELECT ref FROM OBJ.LIST(...)), connection_id => ...)`.
  - **`chunk_size` is in tokens (`[1, 2000]`, default `1000`)** — values `< 1` or `> 2000` fail at query validation (`chunk_size must be in the range [1, 2000]`), and there is no `overlap_size` or `strategy` parameter in the live signature.
  - **Supported formats vs `text/plain` rejection**: Supports PDF (`start_page`/`end_page` 1-indexed), HTML, DOCX, PPTX, and XLSX/XLSM (`start_page`/`end_page` = `0`). Plain `.txt` (`text/plain`) files return `content = NULL` and `status = 'Unsupported input file format: text/plain.'` per row without failing the job; missing GCS blobs return `NULL` across `chunk_id`, `content`, and `status`. Always filter downstream RAG pipelines with `WHERE status = '' AND content IS NOT NULL`.
  - **Required IAM roles on the connection service account**: `roles/storage.objectViewer`, `roles/documentai.apiUser` (or `roles/documentai.editor`), and `roles/serviceusage.serviceUsageConsumer` with `documentai.googleapis.com` enabled. There is no `bbq.ai.chunk_document` wrapper in `bigframes 2.51.0`.
- **`AI.PARSE_DOCUMENT` is retired/offline since 2026-06-01 and its reference page is withdrawn (404)** — `functions/ai_parse_document/` is preserved solely as a historical archive record, while `workflows/document_rag/` is live and built on `AI.CHUNK_DOCUMENT` + `AI.EMBED` + `VECTOR_SEARCH` + `AI.GENERATE`.
- **`ML.PROCESS_DOCUMENT` requires `CREATE MODEL`; `AI.CHUNK_DOCUMENT` does not** — `ML.PROCESS_DOCUMENT` needs a remote model with `REMOTE_SERVICE_TYPE = 'CLOUD_AI_DOCUMENT_V1'` pointing at a pre-provisioned Document AI processor, whereas `AI.CHUNK_DOCUMENT` takes only a `connection_id` and provisions layout-aware chunking automatically.
- **AI functions take an `ObjectRef` directly** (re-read and measured 2026-09-15) — table `ref` columns and `OBJ.MAKE_REF`/`OBJ.FETCH_METADATA` outputs are `ObjectRef` (a STRUCT: `uri`, `version`, `authorizer`, `details` JSON), and that is what every multimodal `AI.*` reference page now documents as the input type. `ObjectRefRuntime` (JSON with `obj_ref` + `access_urls`, produced by `OBJ.GET_ACCESS_URL`) is **still accepted everywhere** — nothing was deprecated — but it is an extra step, and `AI.AGG`'s own known issues warn that arrays of it may be silently skipped. Wrapped and bare were measured side by side across `AI.GENERATE`, `_BOOL`, `_INT`, `_DOUBLE`, `_TABLE`, `AI.IF`, `AI.SCORE`, `AI.CLASSIFY`, `AI.AGG`, `AI.EMBED`, and `AI.SIMILARITY`: all eleven work both ways. **`AI.AGG` is the one page still specifying `ObjectRefRuntime`** — pass it an `ObjectRef` anyway. **`AI.COUNT_TOKENS` is the real exception**: it is text-only and rejects every object form.
- **`EXTERNAL_OBJECT_TRANSFORM` is not required for `AI.CLASSIFY`** (measured 2026-09-15 over a 10-PDF object table) — the bare `ref` column, the transformed column, and an inline `OBJ.MAKE_REF` all return the same classifications. The transform's job is producing a signed URL; that is a real need and not an AI-function need.
- **Omitting the connection from `OBJ.MAKE_REF` changes the access model, not just the syntax** — `OBJ.MAKE_REF(uri)` uses the query runner's own credentials (direct access); `OBJ.MAKE_REF(uri, connection)` uses the connection's service account (delegated access). Delegated is the usual recommendation, **but inside a VPC Service Controls perimeter it inverts**: delegated access mints a signed HTTPS URL that Agent Platform blocks with `INVALID_ARGUMENT: HTTP links are not supported for requests restricted by VPCSC.` Use direct access there.
- **`OBJ.MAKE_REF` performs no validation** — the JSON-input overload accepts `{"uri": "...", "authorizer": "..."}` with no checking; typos surface only later, downstream (e.g., at `OBJ.FETCH_METADATA` or `OBJ.GET_ACCESS_URL`), as an `error`/`runtime_errors` field rather than a query-time failure.
- **`OBJ.FETCH_METADATA` and `OBJ.GET_ACCESS_URL` fail "softly"** — both still return a value on error rather than raising: `OBJ.FETCH_METADATA` puts `{"errors": {"OBJ.FETCH_METADATA": "..."}}` in `details`, and `OBJ.GET_ACCESS_URL` replaces `access_urls` with `runtime_errors`. Downstream code must check for these fields, not rely on query failure.
- **Signed URLs expire in at most 6 hours** — both `OBJ.GET_ACCESS_URL` and Object Table `EXTERNAL_OBJECT_TRANSFORM(... ['SIGNED_URL'])` cap validity at 6 hours (minimum 30 minutes). Never persist `ObjectRefRuntime` values long-term — store the underlying `ObjectRef`, which does not expire, and regenerate a URL only when something outside BigQuery needs one.
- **Object Table `ref` column is allowlist-gated** — the `ref` STRUCT column ("Preview") is only created if the project is on the multimodal data preview allowlist; otherwise the table only exposes `uri`, `content_type`, `size`, `md5_hash`, `updated`, `metadata` and you must build refs manually with `OBJ.MAKE_REF`.
- **Hard 20-connection cap** — `OBJ.MAKE_REF`, `OBJ.FETCH_METADATA`, and `OBJ.GET_ACCESS_URL` all share a limit of 20 distinct connections referenced per project+region in a query; the connection must also be in the same project/region as the query itself.
- **Object Tables require reservations for remote-model processing; inline ObjectRef pipelines don't** — reading an Object Table into a remote-model function (e.g., `AI.GENERATE_EMBEDDING` over an object table) needs a BigQuery reservation, whereas the inline `OBJ.MAKE_REF(uri, connection)` pattern built in a subquery does not (`OBJ.FETCH_METADATA` only if you need content type or size; `OBJ.GET_ACCESS_URL` not at all). This repo's embedding/similarity notebooks all use the inline pattern for that reason. **The image-preprocessing family is stricter still:** `ML.DECODE_IMAGE`, `ML.RESIZE_IMAGE`, `ML.CONVERT_COLOR_SPACE` and `ML.CONVERT_IMAGE_TYPE` need a reservation *whatever* the input — a `FROM_BASE64` literal fails the same way an object table does (verified live 2026-09-11; undocumented). Those four belong to the sibling `bigquery-ml` skill: see its `reference/preprocessing-functions.md` and `narrative/image.md`.
- **One input type, four call shapes** — every multimodal function takes an `ObjectRef`; they differ only in where it goes in the call. **(1) STRUCT prompt** — `STRUCT(prompt, [ref] AS object_refs)` for `AI.GENERATE`/`_BOOL`/`_INT`/`_DOUBLE`/`_TABLE`/`AI.IF`. **(2) Tuple** — `AI.SCORE((text, ref), ...)`. **(3) Direct argument** — `AI.CLASSIFY(ref, categories)`, and `AI.AGG(STRUCT(ref), ...)` in a one-field STRUCT. **(4) `content` parameter** — `AI.EMBED`, `AI.GENERATE_EMBEDDING`, `AI.SIMILARITY`. The old framing of these as four *pipelines* was wrong: only the argument position varies. `VECTOR_SEARCH`, `AI.SEARCH`, `AI.FORECAST`, `AI.DETECT_ANOMALIES`, and `AI.EVALUATE` accept **no** multimodal/ObjectRef input at all — text/numeric only.
- **`ML.PROCESS_DOCUMENT` hard limits**: max 130 pages per document (larger documents error per-row), 120-second timeout per request, requests batched in groups of 10, and models can only be created in **US**/**EU** multi-regions (dataset, connection, and processor must all match).

## Canonical snippet

```sql
-- Option A: Object Table (bulk) + AI.GENERATE on the bare `ref` column
CREATE EXTERNAL TABLE `myproject.mydataset.docs`
WITH CONNECTION `myproject.us.myconnection`
OPTIONS (
  object_metadata = 'SIMPLE',
  uris = ['gs://mybucket/documents/*.pdf']
);

SELECT
  uri,
  (AI.GENERATE(
    STRUCT(
      'Summarize this document in 3 bullet points.' AS prompt,
      [ref] AS object_refs  -- the ObjectRef itself; requires the allowlisted `ref` column
    )
  )).result AS summary
FROM `myproject.mydataset.docs`;

-- Option B: single file, no Object Table needed (OBJ.MAKE_REF)
SELECT (AI.GENERATE(
  STRUCT(
    'Summarize this document in 3 bullet points.' AS prompt,
    [OBJ.MAKE_REF('gs://mybucket/documents/one.pdf', 'myproject.us.myconnection')] AS object_refs
  )
)).result AS summary;

-- Option B2: every PDF under a prefix, still no Object Table (OBJ.LIST, GA)
SELECT uri, (AI.GENERATE(('Summarize this document in 3 bullet points.', ref))).result AS summary
FROM OBJ.LIST('gs://mybucket/documents/*.pdf', 'myproject.us.myconnection');

-- Option C: signed URL — the remaining job for OBJ.GET_ACCESS_URL.
-- Note this is NOT a step toward calling an AI function; it is for handing
-- the object to something outside BigQuery.
SELECT OBJ.GET_READ_URL(ref).url AS display_url   -- fixed 45-minute TTL
FROM `myproject.mydataset.docs`;

-- Option D: layout-aware PDF chunking for RAG with zero CREATE MODEL (AI.CHUNK_DOCUMENT, GA)
SELECT
  ref.uri,
  chunk_id,
  start_page,
  end_page,
  content
FROM AI.CHUNK_DOCUMENT(
  'gs://mybucket/documents/*.pdf',
  connection_id => 'myproject.us.myconnection',
  chunk_size => 500
)
WHERE status = '' AND content IS NOT NULL;
```

## Go deeper

Full extracted notebook walkthroughs live in this skill's `narrative/` folder:

- [`narrative/ai_chunk_document.md`](../narrative/ai_chunk_document.md) (source: `functions/ai_chunk_document/`) — zero-DDL layout-aware document chunking TVF (GA)
- [`narrative/ml_process_document.md`](../narrative/ml_process_document.md) (source: `functions/ml_process_document/`) — specialized Document AI processor extraction (Invoice, Expense, Form, OCR)
- [`narrative/ai_parse_document.md`](../narrative/ai_parse_document.md) (source: `functions/ai_parse_document/`) — historical pre-withdrawal archive of `AI.PARSE_DOCUMENT` (offline since 2026-06-01; superseded by `AI.CHUNK_DOCUMENT` + `ML.PROCESS_DOCUMENT`)
- [`narrative/document_rag.md`](../narrative/document_rag.md) (source: `workflows/document_rag/`) — end-to-end Document RAG workflow built on `AI.CHUNK_DOCUMENT` + `AI.EMBED` + `VECTOR_SEARCH` + `AI.GENERATE`

Object Tables and `OBJ.*` functions have no dedicated function folder — they're infrastructure, not a callable AI function themselves — and are documented in the source repo at `bigquery-ai/reference/unstructured-data-infrastructure.md`.

**Lens 3 per-statement syntax cards (`syntax/`):** [`syntax/INDEX.md`](../syntax/INDEX.md) — [`syntax/aichunk_document.md`](../syntax/aichunk_document.md), [`syntax/aiparse_document.md`](../syntax/aiparse_document.md), [`syntax/mlprocess_document.md`](../syntax/mlprocess_document.md), [`syntax/object-tables.md`](../syntax/object-tables.md), [`syntax/objectref-and-objectrefruntime-schema-reference.md`](../syntax/objectref-and-objectrefruntime-schema-reference.md), [`syntax/objmake_ref.md`](../syntax/objmake_ref.md), [`syntax/objfetch_metadata.md`](../syntax/objfetch_metadata.md), [`syntax/objget_access_url.md`](../syntax/objget_access_url.md), [`syntax/objget_read_url.md`](../syntax/objget_read_url.md), [`syntax/objlist.md`](../syntax/objlist.md), [`syntax/multimodal-input-patterns-by-function.md`](../syntax/multimodal-input-patterns-by-function.md)
