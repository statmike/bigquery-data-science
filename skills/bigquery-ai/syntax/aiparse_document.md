# `AI.PARSE_DOCUMENT`

> **Source:** [`bigquery-ai/reference/document-processing.md#aiparse_document`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ai/reference/document-processing.md#aiparse_document)

- **Description:** Scalar function that parses a document in Cloud Storage (or Google Drive via `ObjectRef`) into structured layout JSON using an auto-provisioned Document AI Layout Parser processor (`bq-created-layout-parser`) — requiring zero `CREATE MODEL` DDL and zero manual processor setup. Returns either flat reading-order blocks (`layout-v1`, default) with HTML tables and normalized bounding boxes, or the full nested Document AI layout tree (`raw-docai`) that can be chained directly into [`AI.CHUNK_DOCUMENT`](aichunk_document.md) as `parsed_document`.
- **Use cases:** Extracting structured reading-order layout blocks (`title`, `heading`, `text`, `table` HTML, `list_item`, `image`, `page_header`, `page_footer`) with page numbers and `[min_y, min_x, max_y, max_x]` bounding boxes; pulling HTML tables out of PDFs, Word documents, PowerPoint decks, Excel workbooks, or HTML pages; and "parse once, chunk many times" pipelines where `AI.PARSE_DOCUMENT(..., options => JSON '{"schema": "raw-docai"}') AS parsed_document` is materialized once and re-chunked at multiple `chunk_size` values via [`AI.CHUNK_DOCUMENT`](aichunk_document.md).
- [documentation](https://docs.cloud.google.com/bigquery/docs/reference/standard-sql/bigqueryml-syntax-ai-parse-document) · [notebook](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ai/functions/ai_parse_document/ai_parse_document.ipynb) · [sql](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ai/functions/ai_parse_document/ai_parse_document.sql)
- **Type:** Scalar function (returns `JSON`) — GA

**Syntax:**
```sql
AI.PARSE_DOCUMENT(
  [document => ] DOCUMENT
  [, connection_id => 'CONNECTION_ID']
  [, options => JSON '{"schema": "layout-v1" | "raw-docai"}']
)
```

> **GOTCHA — Scalar function, not a table-valued function:** In its GA release (`2026-11-02`), `AI.PARSE_DOCUMENT` is a **scalar function** called in `SELECT` that returns a single `JSON` value per row (`SELECT AI.PARSE_DOCUMENT(ref) AS parsed_doc FROM ...`). Never use the legacy early-2026 syntax `FROM AI.PARSE_DOCUMENT(TABLE ..., endpoint => '...')` — calling `AI.PARSE_DOCUMENT` after `FROM` or `JOIN` or passing `endpoint =>` is a syntax error.

**Inputs:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `document` | `STRING` or `STRUCT` (`ObjectRef`) | Required | -- | Document to parse: either a Cloud Storage URI string (`'gs://bucket/path/file.pdf'`, positional or named `document =>`) or an `ObjectRef` `STRUCT` from an object table's `ref` column, `OBJ.LIST(...)`, or `OBJ.MAKE_REF(...)` (including Google Drive files passed as `ObjectRef`). Unlike `AI.CHUNK_DOCUMENT`, `AI.PARSE_DOCUMENT` does not expand `'gs://.../*.pdf'` wildcards on a raw `STRING` argument — use `FROM OBJ.LIST('gs://bucket/docs/*.pdf')` to parse multiple files. |
| `connection_id` | `STRING` (named parameter) | Optional | End-user credentials | Cloud resource connection (`'PROJECT_ID.LOCATION.CONNECTION_ID'` or `'LOCATION.CONNECTION_ID'`) whose service account accesses Cloud Storage and Document AI instead of caller end-user credentials (EUC). When `document` is a 2-argument `OBJ.MAKE_REF(uri, connection)` or an object table's `ref` column, `connection_id` must match `ref.authorizer` (or be omitted to inherit `ref.authorizer`). |
| `options` | `JSON` (named parameter) | Optional | `JSON '{"schema": "layout-v1"}'` | Output JSON schema selector: `JSON '{"schema": "layout-v1"}'` (default flat reading-order blocks) or `JSON '{"schema": "raw-docai"}'` (full nested Document AI `DocumentLayoutBlock` tree, required when chaining into [`AI.CHUNK_DOCUMENT`](aichunk_document.md)). Passing an unknown schema name raises an analysis-time `400 Unsupported document parsing schema` error. |

**Output (`JSON`):**

Top-level JSON object:
```json
{
  "metadata": { "schema": "layout-v1" },
  "blocks": [ ... ],
  "errors": [ { "code": "...", "message": "..." } ]
}
```
*(The `errors` array is omitted when parsing succeeds.)*

**Comparing the two output schemas (`layout-v1` vs `raw-docai`):**

| Property | `layout-v1` *(default)* | `raw-docai` |
|----------|-------------------------|-------------|
| **`options` argument** | Omit `options` or pass `options => JSON '{"schema": "layout-v1"}'` | `options => JSON '{"schema": "raw-docai"}'` |
| **`blocks` structure** | **Flat array** of blocks in reading order (`UNNEST(JSON_QUERY_ARRAY(parsed.blocks))`) | **Nested tree** of Document AI `DocumentLayoutBlock` objects (`textBlock.blocks`, `tableBlock.bodyRows`, `listBlock.listEntries`) |
| **Field naming** | `snake_case`: `id`, `type`, `content`, `page_number`, `bbox` | `camelCase`: `blockId`, `pageSpan` (`pageStart`, `pageEnd`), `boundingBox`, `textBlock` / `tableBlock` / `listBlock` |
| **Block `type` values (`layout-v1`)** | `'title'`, `'heading'`, `'text'`, `'table'` (`content` is an HTML `<table>...</table>` string), `'list_item'`, `'image'`, `'page_header'`, `'page_footer'` | Nested `textBlock.type` (`'paragraph'`, `'heading-1'`, etc.), `tableBlock`, `listBlock` |
| **Bounding boxes (`bbox`)** | 4-element `FLOAT64` array `[min_y, min_x, max_y, max_x]` normalized to `[0, 1]` (`null` when bounding boxes are not applicable) | `boundingBox.normalizedVertices` |
| **Accepted by `AI.CHUNK_DOCUMENT`?** | **No** — returns per-row `status = 'INVALID_ARGUMENT: Unsupported document schema: layout-v1'` | **Yes** — alias the output column `AS parsed_document` and pass the table/subquery to `AI.CHUNK_DOCUMENT` |

**Per-row error handling (`NULL` vs `errors` array vs query error):**

| Scenario | Behavior |
|----------|----------|
| Valid supported document (`<= 130` pages) | Returns `{ "metadata": {"schema": "..."}, "blocks": [...] }` (`JSON_QUERY(parsed, '$.errors') IS NULL`) |
| `document` argument is SQL `NULL` | Returns SQL `NULL` |
| Unsupported MIME type (e.g., `text/plain`, `.md`, standalone image) or `> 130` pages | Query succeeds; returns `{ "blocks": [], "errors": [{"code": "INVALID_ARGUMENT", "message": "..."}], "metadata": {...} }` |
| Missing GCS object (`'gs://bucket/missing.pdf'` or `OBJ.MAKE_REF`) | Query succeeds; returns `{ "blocks": [], "errors": [{"code": "NOT_FOUND", "message": "No such object: ..."}], "metadata": {...} }` |
| Invalid `options` schema (e.g., `'{"schema": "v2"}'`) | Fails query validation with `400 Unsupported document parsing schema` |

Always check `JSON_QUERY(parsed_doc, '$.errors') IS NULL` (or `ARRAY_LENGTH(JSON_QUERY_ARRAY(parsed_doc, '$.blocks')) > 0`) to filter out per-row `INVALID_ARGUMENT` / `NOT_FOUND` results.

**Examples:**
```sql
-- 1. Parse a single PDF in Cloud Storage and unpack reading-order layout-v1 blocks
WITH parsed AS (
  SELECT AI.PARSE_DOCUMENT('gs://BUCKET_NAME/sample_invoice.pdf') AS doc
)
SELECT
  STRING(block.id) AS block_id,
  STRING(block.type) AS block_type,
  INT64(block.page_number) AS page_number,
  STRING(block.content) AS content,
  block.bbox AS bbox_ymin_xmin_ymax_xmax
FROM parsed,
UNNEST(JSON_QUERY_ARRAY(doc.blocks)) AS block;

-- 2. Parse multiple documents via OBJ.LIST with raw-docai and chain into AI.CHUNK_DOCUMENT
CREATE OR REPLACE TABLE `your-gcp-project-id.DATASET_ID.parsed_docs` AS
SELECT
  uri,
  AI.PARSE_DOCUMENT(
    ref,
    options => JSON '{"schema": "raw-docai"}'
  ) AS parsed_document
FROM OBJ.LIST('gs://BUCKET_NAME/manuals/*.pdf');

-- Re-chunk the pre-parsed table at any chunk_size without re-calling Document AI
SELECT uri, chunk_id, start_page, end_page, content
FROM AI.CHUNK_DOCUMENT(
  TABLE `your-gcp-project-id.DATASET_ID.parsed_docs`,
  chunk_size => 300
)
WHERE status = ''
ORDER BY uri, chunk_id;
```

**Supported file types and limits:**
- **Supported formats:** PDF (`.pdf`), HTML (`.html`), Word OOXML (`.docx`), PowerPoint OOXML (`.pptx`), and Excel OOXML (`.xlsx`).
- **Unsupported formats:** Plain text (`.txt`), Markdown (`.md`), and standalone raster images (`.png`, `.jpg`, `.tiff`, etc.) return a per-row `INVALID_ARGUMENT` entry in `$.errors`. Use [`ML.PROCESS_DOCUMENT`](mlprocess_document.md) with an OCR or specialized processor for standalone images.
- **Page limit:** Maximum **130 pages per document**. Documents exceeding 130 pages return a per-row `INVALID_ARGUMENT` in `$.errors` (for PDFs up to 500 pages that only need RAG chunks, call [`AI.CHUNK_DOCUMENT`](aichunk_document.md) directly on the `'gs://...'` URI or `ObjectRef`).

**Auto-provisioned processor, IAM & VPC-SC:**
- Uses the same auto-provisioned `bq-created-layout-parser` Document AI Layout Parser processor ($0 idle fee), `documentai.googleapis.com` API, and IAM roles (`roles/documentai.editor` on first call in a region, `roles/documentai.viewer` thereafter, plus `roles/storage.objectViewer`) as [`AI.CHUNK_DOCUMENT`](aichunk_document.md).
- **VPC Service Controls (VPC-SC):** Inside a VPC-SC perimeter, pass a direct `'gs://...'` URI string or 1-argument `OBJ.MAKE_REF(uri)` under end-user credentials rather than a connection-backed `ObjectRef` or object table.

**Locations:** Supported in the **`US`** and **`EU`** multi-regions and in US and EU single regions **excluding London (`europe-west2`) and Zurich (`europe-west6`)**.

**Pricing & Provisioned throughput:** Billed at standard Document AI Layout Parser rates (**$10 per 1,000 pages** processed) plus BigQuery query compute; `bq-created-layout-parser` incurs zero idle fee.

**BigFrames API:** As of `bigframes 2.53.0`, there is no dedicated `bigframes.bigquery.ai.parse_document()` wrapper; execute via `bpd.read_gbq_query("SELECT AI.PARSE_DOCUMENT(...) AS parsed_doc ...")`.
