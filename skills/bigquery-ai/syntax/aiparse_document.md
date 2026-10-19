# `AI.PARSE_DOCUMENT`

> **Source:** [`bigquery-ai/reference/document-processing.md#aiparse_document`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ai/reference/document-processing.md#aiparse_document)

- **⚠️ Status (as of 2026-09-01): OFFLINE, and reference documentation now WITHDRAWN.** The function (Preview) was taken offline by Google for revision on 2026-06-01 and does not execute. As of this audit the situation has escalated: the reference page `.../bigqueryml-syntax-ai-parse-document` returns **HTTP 404**, the function no longer appears in the BigQuery docs navigation tree, and it is absent from the generative AI overview page. Google has published no release note explaining the withdrawal.
  - **Interim alternative:** use [`ML.PROCESS_DOCUMENT`](mlprocess_document.md) for OCR and document extraction. It reaches the same Document AI processors but requires a remote model and a `CREATE MODEL` step — precisely the setup AI.PARSE_DOCUMENT was introduced to remove.
  - **Affected content:** `functions/ai_parse_document/` and `workflows/document_rag/` carry warning banners. Their committed outputs are a record of the function working before 2026-06-01, not current behavior. Do not re-run them.
  - **Re-check** the [BigQuery release notes](https://docs.cloud.google.com/bigquery/docs/release-notes). If it returns, reverse this note, remove the notebook banners, and re-run to verify (precedent: AI.AGG disable Apr 2026 → re-enable May 2026). Documentation below is retained from the last published version of the page — treat it as an archived snapshot, not a live reference.
- **Description:** (Preview) Table-valued function that parses documents using the Document AI Layout Parser. Combines OCR, layout parsing, and chunking into a single SQL function call — no `CREATE MODEL` step required. The `endpoint` parameter points directly to a Document AI Layout Parser processor.
- **Use cases:** Document text extraction, chunking for RAG pipelines, OCR from scanned documents, layout-aware document parsing.
- [documentation](https://docs.cloud.google.com/bigquery/docs/reference/standard-sql/bigqueryml-syntax-ai-parse-document) — **dead link (HTTP 404 as of 2026-09-01)**, retained so the page can be re-checked if the function returns
- **Type:** Table-valued function (returns a table) — Preview

**Syntax:**
```sql
SELECT *
FROM AI.PARSE_DOCUMENT(
  { TABLE `PROJECT_ID.DATASET.OBJECT_TABLE` | (QUERY_STATEMENT) },
  endpoint => 'projects/PROJECT_NUM/locations/LOCATION/processors/PROCESSOR_ID'
  [, chunk_size => CHUNK_SIZE ]
  [, connection_id => 'PROJECT_ID.LOCATION.CONNECTION_ID' ]
);
```

**Inputs:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `TABLE` / `(QUERY_STATEMENT)` | Table or subquery | Required | -- | Object table reference or a `SELECT` subquery. Must include a column named `ref` of type `OBJECTREF`. Can be an object table (which has `ref` built-in) or a subquery that constructs `ref` using `OBJ.MAKE_REF(uri, connection) AS ref`. |
| `endpoint` | STRING (named parameter) | Required | -- | Document AI Layout Parser processor endpoint. Format: `projects/{project}/locations/{location}/processors/{processor_id}`. |
| `chunk_size` | INT64 (named parameter) | Optional | ~1000 | Controls the size of text chunks when splitting documents. Smaller values (e.g., 250) produce more granular chunks for RAG pipelines. |
| `connection_id` | STRING (named parameter) | Optional | End-user credentials | BigQuery Cloud resource connection. Format: `PROJECT_ID.LOCATION.CONNECTION_ID`. Connection service account needs `documentai.apiUser` and `storage.objectViewer` roles. |

**Outputs:**

| Column | Type | Description |
|--------|------|-------------|
| `chunk_id` | INT64 | Sequence ID of an extracted document chunk, starting from 1. |
| `start_page` | INT64 | Page number where the chunk starts. |
| `end_page` | INT64 | Page number where the chunk ends. |
| `content` | STRING | Extracted text content of the chunk. |
| *(object table columns)* | *(varies)* | All columns from the input object table or query are passed through (e.g., `uri`, `content_type`). |

**Supported file types:** Same as ML.PROCESS_DOCUMENT — PDF, JPEG, PNG, BMP, GIF, TIFF, WebP, plus HTML, DOCX, PPTX, XLSX (Layout Parser only).

**ObjectRef alternative (no object table required):**

AI.PARSE_DOCUMENT requires a `ref` column in its input. Object tables provide this automatically, but you can also construct it inline using `OBJ.MAKE_REF`:

```sql
-- Single document — no object table needed
SELECT *
FROM AI.PARSE_DOCUMENT(
  (SELECT
    'gs://BUCKET/document.pdf' AS uri,
    OBJ.MAKE_REF('gs://BUCKET/document.pdf', 'PROJECT_ID.LOCATION.CONNECTION_ID') AS ref
  ),
  endpoint => 'projects/PROJECT_NUM/locations/LOCATION/processors/PROCESSOR_ID'
);

-- Multiple documents — use UNNEST
SELECT *
FROM AI.PARSE_DOCUMENT(
  (SELECT
    uri,
    OBJ.MAKE_REF(uri, 'PROJECT_ID.LOCATION.CONNECTION_ID') AS ref
  FROM UNNEST(['gs://BUCKET/doc1.pdf', 'gs://BUCKET/doc2.pdf']) AS uri),
  endpoint => 'projects/PROJECT_NUM/locations/LOCATION/processors/PROCESSOR_ID'
);
```

This is useful for ad-hoc parsing of specific documents without creating an object table first.

**Best practices:**
- Filter documents with `WHERE`/`LIMIT` in a subquery rather than processing the entire object table.
- Use `CREATE TABLE ... AS SELECT` to persist results and avoid re-processing.
- For RAG pipelines, use `chunk_size => 250` for more granular retrieval precision.
- Minimum 200 dpi for document scans; 300 dpi or higher recommended.

**Limitations:**
- Maximum **130 pages per document**. Rows with larger documents return an error.
- **Layout Parser only** — does not support other Document AI processor types (use ML.PROCESS_DOCUMENT for invoice, receipt, form, OCR, or custom processors).
- Requires creating a Document AI Layout Parser processor first (but no `CREATE MODEL` step).

**Locations:** The dataset, connection, and Document AI processor must all be in the **US** or **EU** multi-regions.

**Provisioned throughput:** Not specified. Subject to Document AI API quotas.

**BigFrames API:** No direct equivalent. Use `%%bigquery` magics or `session.read_gbq_query()` to execute AI.PARSE_DOCUMENT SQL from BigFrames.

**Relationship to ML.PROCESS_DOCUMENT:** AI.PARSE_DOCUMENT is to ML.PROCESS_DOCUMENT what AI.GENERATE is to AI.GENERATE_TEXT — a simplified alternative that skips the `CREATE MODEL` step. Use ML.PROCESS_DOCUMENT when you need specialized processors (invoice, form, custom) or full `PROCESS_OPTIONS` control. Use AI.PARSE_DOCUMENT for straightforward OCR + chunking workflows.
