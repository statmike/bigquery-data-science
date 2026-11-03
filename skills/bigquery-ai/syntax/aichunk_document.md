# `AI.CHUNK_DOCUMENT`

> **Source:** [`bigquery-ai/reference/document-processing.md#aichunk_document`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ai/reference/document-processing.md#aichunk_document)

- **Description:** Table-valued function that splits unstructured documents in Cloud Storage into layout-aware text chunks using an auto-provisioned Document AI Layout Parser processor (`bq-created-layout-parser`) — requiring zero `CREATE MODEL` DDL and zero manual Document AI processor setup.
- **Use cases:** Layout-aware chunking of PDFs, Word documents, PowerPoint decks, Excel workbooks, and HTML pages for RAG pipelines (`AI.CHUNK_DOCUMENT` -> `AI.EMBED` -> `VECTOR_SEARCH` / `AI.SEARCH`), section-preserving document ingestion with ancestor headings, ad-hoc single-URI or wildcard GCS document parsing without creating an object table.
- [documentation](https://cloud.google.com/bigquery/docs/reference/standard-sql/bigqueryml-syntax-ai-chunk-document) · [notebook](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ai/functions/ai_chunk_document/ai_chunk_document.ipynb) · [sql](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ai/functions/ai_chunk_document/ai_chunk_document.sql)
- **Type:** Table-valued function (returns a table) — GA

**Syntax:**
```sql
SELECT *
FROM AI.CHUNK_DOCUMENT(
  { 'STORAGE_URI' | TABLE input_table | (query_statement) }
  [, connection_id => 'CONNECTION_ID']
  [, chunk_size => CHUNK_SIZE]
);
```

**Inputs:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `'STORAGE_URI'` \| `TABLE input_table` \| `(query_statement)` | `STRING` literal, object table, or subquery | Required | -- | Document source: (1) a Cloud Storage `'gs://bucket/path/file.pdf'` URI or `'gs://bucket/docs/*.pdf'` wildcard string literal, (2) a BigQuery `EXTERNAL` object table (`TABLE project.dataset.object_table`), or (3) a parenthesized `SELECT` subquery returning an `OBJECTREF` column **named `ref`** (for example via `OBJ.MAKE_REF(uri) AS ref` or `OBJ.LIST(...)`, optionally alongside additional passthrough columns). |
| `connection_id` | `STRING` (named parameter) | Optional (required for `TABLE object_table`) | End-user credentials | Cloud resource connection (`'PROJECT_ID.LOCATION.CONNECTION_ID'` or `'LOCATION.CONNECTION_ID'`) whose service account accesses Cloud Storage and Document AI instead of caller end-user credentials (EUC). Required when reading `TABLE object_table` (must match the object table's connection); on `(query_statement)`, must match `ref.authorizer` (or be omitted for 1-arg `OBJ.MAKE_REF(uri)`); on `'gs://...'` URI literals, upstream docs state EUC-only though live `2026-11-02` probes confirmed `connection_id` is also accepted. |
| `chunk_size` | `INT64` (named parameter) | Optional | `1000` | Target chunk size in tokens. Must be an `INT64` literal in `[1, 2000]`; values outside `1..2000` fail query validation. Smaller values (such as `chunk_size => 250` or `chunk_size => 500`) yield finer-grained RAG retrieval units while still prepending ancestor section headings. |

**Three input shapes and output column counts:**

| Input Shape | SQL Pattern | Output Columns | URI Column Access |
|-------------|-------------|----------------|-------------------|
| **1. Storage URI / wildcard** | `AI.CHUNK_DOCUMENT('gs://bucket/docs/*.pdf', chunk_size => 500)` | **13 columns** (`5` chunk columns + `8` object metadata columns: `uri`, `generation`, `content_type`, `size`, `md5_hash`, `updated`, `metadata`, `ref`) | Top-level `uri` |
| **2. Object table** | `AI.CHUNK_DOCUMENT(TABLE \`PROJECT_ID.DATASET.OBJECT_TABLE\`, chunk_size => 500)` | **13 columns** (`5` chunk columns + the object table's `8` columns) | Top-level `uri` |
| **3. `ObjectRef` subquery** | `AI.CHUNK_DOCUMENT((SELECT doc_id, OBJ.MAKE_REF(uri) AS ref FROM ...), chunk_size => 500)` | **`5 + N` columns** (`5` chunk columns + the `N` columns projected by the subquery) | `ref.uri` unless the subquery also projected `uri` explicitly |

> **GOTCHA — Subquery `ref` column binding & passthrough columns:** The `(query_statement)` form binds its input column **by exact column name (`ref`)**, not by column count (`AI.CHUNK_DOCUMENT expects the input table to have a column named 'ref' or 'parsed_document', but both are missing.`). When `(query_statement)` selects only `OBJ.MAKE_REF(uri) AS ref`, `AI.CHUNK_DOCUMENT` returns **6 columns** (`chunk_id`, `content`, `start_page`, `end_page`, `status`, `ref`) with **no top-level `uri` column** — read `ref.uri` or project `uri` alongside `ref` in the subquery.

**Outputs (core chunk columns):**

| Column | Type | Description |
|--------|------|-------------|
| `chunk_id` | `INT64` | 1-indexed sequential chunk number within each source document (`NULL` when chunking fails for that object). |
| `content` | `STRING` | Layout-aware extracted chunk text with ancestor headings prepended for hierarchical context (`NULL` on error). |
| `start_page` | `INT64` | 1-indexed page number where the chunk begins (`NULL` on error). Because ancestor headings from an earlier page can be prepended to a chunk on a later page, `start_page..end_page` ranges frequently overlap across consecutive chunks. |
| `end_page` | `INT64` | 1-indexed page number where the chunk ends (`NULL` on error). |
| `status` | `STRING` | Per-document processing status: `''` (empty string) on success, a non-empty error string when Document AI rejects a file, or `NULL` when an `OBJ.MAKE_REF` URI points to a missing GCS object. |
| *(passthrough columns)* | *(varies)* | Either the 8 object-metadata columns (`'gs://...'` and `TABLE` forms) or the exact columns projected by `(query_statement)`. |

**GOTCHA — Three-way `status` contract (`''` vs error string vs `NULL`):**

| Scenario | `status` value | `chunk_id` / `content` |
|----------|----------------|------------------------|
| Valid supported document | `''` (empty string) | Populated (`1..K`, extracted text) |
| Unsupported format (`.txt`, `.md`, `.png`) or page/size limit exceeded | Non-empty error message (`STRING`) | `NULL` |
| Missing GCS object passed via `OBJ.MAKE_REF('gs://bucket/missing.pdf')` | `NULL` (does **not** fail the query job) | `NULL` |

Always filter downstream RAG and embedding pipelines with `WHERE status = ''` — in GoogleSQL, `status = ''` keeps valid chunks and excludes **both** non-empty error strings and `NULL` missing-object rows (`WHERE status IS NULL` would keep *only* broken missing-URI rows!).

**Examples:**
```sql
-- 1. Direct GCS URI or wildcard under caller end-user credentials (no DDL)
SELECT uri, chunk_id, start_page, end_page, content
FROM AI.CHUNK_DOCUMENT(
  'gs://BUCKET_NAME/manuals/*.pdf',
  chunk_size => 500
)
WHERE status = ''
ORDER BY uri, chunk_id;

-- 2. Subquery with 1-argument OBJ.MAKE_REF(uri) + passthrough document metadata
SELECT doc_id, ref.uri AS gcs_uri, chunk_id, content
FROM AI.CHUNK_DOCUMENT(
  (
    SELECT doc_id, OBJ.MAKE_REF(gcs_uri) AS ref
    FROM `your-gcp-project-id.DATASET_ID.document_catalog`
  ),
  chunk_size => 300
)
WHERE status = '';
```

**Supported file types and size limits:**
- **Supported formats:** PDF (`.pdf`), HTML (`.html`), Word OOXML (`.docx`), PowerPoint OOXML (`.pptx`), and Excel OOXML (`.xlsx`, `.xlsm`).
- **Unsupported formats:** Plain text (`.txt`), Markdown (`.md`), and standalone raster images (`.png`, `.jpg`, `.jpeg`, `.gif`, `.tiff`, `.bmp`, `.webp`) return non-empty per-row `status` errors. Chunk `.txt`/`.md` directly in SQL or use [`ML.PROCESS_DOCUMENT`](mlprocess_document.md) with an OCR/specialized processor for standalone images.
- **Size and page limits:** Up to **20 MB / 15 pages** on the synchronous Document AI path, and up to **1 GB / 500 pages** on the batch PDF path.

**Auto-provisioned processor & IAM prerequisites:**
1. Enable the Cloud Document AI API (`documentai.googleapis.com`) in the billing/execution project.
2. On the **first** `AI.CHUNK_DOCUMENT` call in a region, BigQuery automatically creates a Document AI Layout Parser processor named `bq-created-layout-parser` in that region and reuses it on all subsequent calls (Document AI Layout Parser processors have **zero idle hosting cost**).
3. **IAM roles** (on the caller for EUC, or on `bqcx-000000000000-xxxx@gcp-sa-bigquery-condel.iam.gserviceaccount.com` when `connection_id` is supplied):
   - `roles/documentai.editor` for the **first** run in a region so BigQuery can create `bq-created-layout-parser` (`roles/documentai.viewer` suffices once `bq-created-layout-parser` already exists).
   - `roles/storage.objectViewer` on the source Cloud Storage bucket.

**GOTCHA — VPC Service Controls (VPC-SC) perimeter restriction:**
Inside a VPC-SC perimeter, passing an object table or 2-argument connection-backed `OBJ.MAKE_REF(uri, connection_id)` fails with:
`INVALID_ARGUMENT: HTTP links are not supported for requests restricted by VPCSC.`
because connection-backed `ObjectRef` resolution mints signed HTTPS access URLs. Inside VPC-SC, call `AI.CHUNK_DOCUMENT` with a direct `'gs://...'` URI literal or 1-argument `OBJ.MAKE_REF(uri)` under end-user credentials.

**Best practices:**
- Persist chunked output with `CREATE TABLE ... AS SELECT ... FROM AI.CHUNK_DOCUMENT(...) WHERE status = ''` before calling `AI.EMBED` so documents are parsed once rather than re-billed on every query.
- Inspect failed documents separately with `WHERE status IS NOT NULL AND status != ''` (Document AI errors) and `WHERE status IS NULL` (missing `OBJ.MAKE_REF` URIs).
- Tune `chunk_size` (`250`–`500` tokens for dense Q&A retrieval, `1000` default for broader passage context); ancestor headings are automatically prepended so small chunks retain section context.

**Locations:** Supported in the **`US`** and **`EU`** multi-regions and in US and EU single regions **excluding London (`europe-west2`) and Zurich (`europe-west6`)**.

**Pricing & Provisioned throughput:** Billed at standard Document AI Layout Parser rates (**$10 per 1,000 pages** processed) plus BigQuery query compute; `bq-created-layout-parser` incurs zero idle fee. Subject to Document AI Layout Parser quotas rather than Vertex AI Gemini Provisioned Throughput.

**BigFrames API:** As of `bigframes 2.51.0`, there is no dedicated `bigframes.bigquery.ai.chunk_document()` wrapper; execute via `bpd.read_gbq_query("SELECT * FROM AI.CHUNK_DOCUMENT(...)")`.

---
