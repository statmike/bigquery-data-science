![tracker](https://us-central1-vertex-ai-mlops-369716.cloudfunctions.net/pixel-tracking?path=statmike%2Fbigquery-data-science%2Fbigquery-ai%2Freference&file=document-processing.md)
<!--- header table --->
<table>
<tr>     
  <td style="text-align: center">
    <a href="https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ai/reference/document-processing.md">
      <img width="32px" src="https://raw.githubusercontent.com/statmike/bigquery-data-science/main/architectures/headers/icons/github.svg" alt="GitHub logo">
      <br>View on<br>GitHub
    </a>
  </td>
</tr>
<tr>
  <td style="text-align: right">
    <b>Share On: </b> 
    <a href="https://www.linkedin.com/sharing/share-offsite/?url=https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ai/reference/document-processing.md"><img src="https://raw.githubusercontent.com/statmike/bigquery-data-science/main/architectures/headers/icons/linkedin.svg" alt="Linkedin Logo" width="20px"></a> 
    <a href="https://reddit.com/submit?url=https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ai/reference/document-processing.md"><img src="https://raw.githubusercontent.com/statmike/bigquery-data-science/main/architectures/headers/icons/reddit.png" alt="Reddit Logo" width="20px"></a> 
    <a href="https://bsky.app/intent/compose?text=https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ai/reference/document-processing.md"><img src="https://raw.githubusercontent.com/statmike/bigquery-data-science/main/architectures/headers/icons/bluesky.svg" alt="BlueSky Logo" width="20px"></a> 
    <a href="https://x.com/intent/post?url=https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ai/reference/document-processing.md"><img src="https://raw.githubusercontent.com/statmike/bigquery-data-science/main/architectures/headers/icons/x.svg" alt="X (Twitter) Logo" width="20px"></a> 
  </td>
</tr>
<tr>
  <td style="text-align: right">
    <b>Connect With Author On: </b> 
    <a href="https://www.linkedin.com/in/statmike"><img src="https://raw.githubusercontent.com/statmike/bigquery-data-science/main/architectures/headers/icons/linkedin.svg" alt="Linkedin Logo" width="20px"></a>
    <a href="https://github.com/statmike"><img src="https://raw.githubusercontent.com/statmike/bigquery-data-science/main/architectures/headers/icons/github.svg" alt="GitHub Logo" width="20px"></a> 
    <a href="https://www.youtube.com/@statmike-channel"><img src="https://raw.githubusercontent.com/statmike/bigquery-data-science/main/architectures/headers/icons/youtube.svg" alt="YouTube Logo" width="20px"></a>
    <a href="https://bsky.app/profile/statmike.bsky.social"><img src="https://raw.githubusercontent.com/statmike/bigquery-data-science/main/architectures/headers/icons/bluesky.svg" alt="BlueSky Logo" width="20px"></a> 
    <a href="https://x.com/statmike"><img src="https://raw.githubusercontent.com/statmike/bigquery-data-science/main/architectures/headers/icons/x.svg" alt="X (Twitter) Logo" width="20px"></a>
  </td>
</tr>
<tr>
  <td style="text-align: right">
    <a href="https://raw.githubusercontent.com/statmike/bigquery-data-science/main/bigquery-ai/reference/document-processing.md"><img src="https://raw.githubusercontent.com/statmike/bigquery-data-science/main/architectures/headers/icons/download.svg" alt="Download icon" width="20px"></a> <a href="https://raw.githubusercontent.com/statmike/bigquery-data-science/main/bigquery-ai/reference/document-processing.md">Download File</a> <i>(right-click and "Save As")</i>
  </td>
</tr>
</table><br/><br/>

---
# Document Processing

> Part of the [BigQuery AI Functions Resources](../RESOURCES.md) · [Project README](../README.md)

These functions process unstructured documents (PDFs, Office files, HTML, images, forms, invoices) using Document AI processors, returning layout-aware chunks, structured layout JSON, or specialized entity extractions directly as BigQuery columns.

| Capability | [`AI.CHUNK_DOCUMENT`](#aichunk_document) | [`AI.PARSE_DOCUMENT`](#aiparse_document) | [`ML.PROCESS_DOCUMENT`](#mlprocess_document) |
|------------|------------------------------------------|------------------------------------------|----------------------------------------------|
| **Release status** | GA | GA | GA |
| **Function type** | Table-valued function (TVF) | Scalar function (`-> JSON`) | Table-valued function (TVF) |
| **Prerequisite DDL** | None — auto-provisions `bq-created-layout-parser` on first run | None — auto-provisions `bq-created-layout-parser` on first run | `CREATE MODEL ... REMOTE_SERVICE_TYPE = 'CLOUD_AI_DOCUMENT_V1'` + pre-created Document AI processor |
| **Processor coverage** | Document AI Layout Parser only (layout-aware RAG chunking) | Document AI Layout Parser only (`layout-v1` reading-order blocks or `raw-docai` layout tree) | All 16 Document AI processor types (Invoice, Expense, Form, OCR, W2, Custom, Layout Parser, etc.) |
| **Input forms** | `'gs://...'` URI/wildcard literal, `TABLE object_table`, `(SELECT ... ObjectRef)` subquery, or `TABLE`/`(SELECT ...)` with a `parsed_document` (`raw-docai`) JSON column | `'gs://...'` URI string or `ObjectRef` (`STRUCT`, including Google Drive files passed as `ObjectRef`) | `TABLE object_table` or constrained `SELECT` subquery over an object table |
| **Max document size** | Up to **500 pages / 1 GB** (batch PDF path); **15 pages / 20 MB** (sync path); **130 pages** via `AI.PARSE_DOCUMENT` | Up to **130 pages** per document (`$0` idle hosting fee) | Up to **130 pages** per document (`120s` per-request timeout) |
| **Supported formats** | PDF, HTML, DOCX, PPTX, XLSX, XLSM *(no standalone raster images, `.txt`, or `.md`)* | PDF, HTML, DOCX, PPTX, XLSX *(no standalone raster images, `.txt`, or `.md`)* | PDF, GIF, TIFF, JPEG, PNG, BMP, WebP, plus HTML, DOCX, PPTX, XLSX (Layout Parser) |

> **"Parse once, chunk many times":** [`AI.PARSE_DOCUMENT`](#aiparse_document) called with `options => JSON '{"schema": "raw-docai"}'` returns the full nested Document AI `DocumentLayoutBlock` tree as a `JSON` column. When materialized into a table and aliased `AS parsed_document`, [`AI.CHUNK_DOCUMENT`](#aichunk_document) can re-chunk that pre-parsed table at any `chunk_size` in seconds without re-calling Document AI or re-paying the per-page parsing fee.

---

## `AI.CHUNK_DOCUMENT`
- **Description:** Table-valued function that splits unstructured documents in Cloud Storage (or pre-parsed `raw-docai` JSON from [`AI.PARSE_DOCUMENT`](#aiparse_document)) into layout-aware text chunks using an auto-provisioned Document AI Layout Parser processor (`bq-created-layout-parser`) — requiring zero `CREATE MODEL` DDL and zero manual Document AI processor setup.
- **Use cases:** Layout-aware chunking of PDFs, Word documents, PowerPoint decks, Excel workbooks, and HTML pages for RAG pipelines (`AI.CHUNK_DOCUMENT` -> `AI.EMBED` -> `VECTOR_SEARCH` / `AI.SEARCH`), re-chunking pre-parsed `AI.PARSE_DOCUMENT(..., options => JSON '{"schema": "raw-docai"}')` tables across multiple `chunk_size` experiments, section-preserving document ingestion with ancestor headings, ad-hoc single-URI or wildcard GCS document parsing without creating an object table.
- [documentation](https://cloud.google.com/bigquery/docs/reference/standard-sql/bigqueryml-syntax-ai-chunk-document) · [notebook](../functions/ai_chunk_document/ai_chunk_document.ipynb) · [sql](../functions/ai_chunk_document/ai_chunk_document.sql)
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
| `'STORAGE_URI'` \| `TABLE input_table` \| `(query_statement)` | `STRING` literal, table, or subquery | Required | -- | Document source: (1) a Cloud Storage `'gs://bucket/path/file.pdf'` URI or `'gs://bucket/docs/*.pdf'` wildcard string literal, (2) a BigQuery `EXTERNAL` object table (`TABLE project.dataset.object_table`), (3) a parenthesized `SELECT` subquery returning an `OBJECTREF` column **named `ref`** (for example via `OBJ.MAKE_REF(uri) AS ref` or `OBJ.LIST(...)`, optionally alongside additional passthrough columns), or (4) a `TABLE` or `(query_statement)` containing a `JSON` column **named `parsed_document`** produced by `AI.PARSE_DOCUMENT(..., options => JSON '{"schema": "raw-docai"}')`. |
| `connection_id` | `STRING` (named parameter) | Optional (required for `TABLE object_table`) | End-user credentials | Cloud resource connection (`'PROJECT_ID.LOCATION.CONNECTION_ID'` or `'LOCATION.CONNECTION_ID'`) whose service account accesses Cloud Storage and Document AI instead of caller end-user credentials (EUC). Required when reading `TABLE object_table` (must match the object table's connection); on `(query_statement)`, must match `ref.authorizer` (or be omitted for 1-arg `OBJ.MAKE_REF(uri)` or `parsed_document` inputs); on `'gs://...'` URI literals, upstream docs state EUC-only though live `2026-11-02` probes confirmed `connection_id` is also accepted. |
| `chunk_size` | `INT64` (named parameter) | Optional | `1000` | Target chunk size in tokens. Must be an `INT64` literal in `[1, 2000]`; values outside `1..2000` fail query validation. Smaller values (such as `chunk_size => 250` or `chunk_size => 500`) yield finer-grained RAG retrieval units while still prepending ancestor section headings. |

**Four input shapes and output column counts:**

| Input Shape | SQL Pattern | Output Columns | URI Column Access |
|-------------|-------------|----------------|-------------------|
| **1. Storage URI / wildcard** | `AI.CHUNK_DOCUMENT('gs://bucket/docs/*.pdf', chunk_size => 500)` | **13 columns** (`5` chunk columns + `8` object metadata columns: `uri`, `generation`, `content_type`, `size`, `md5_hash`, `updated`, `metadata`, `ref`) | Top-level `uri` |
| **2. Object table** | `AI.CHUNK_DOCUMENT(TABLE \`PROJECT_ID.DATASET.OBJECT_TABLE\`, chunk_size => 500)` | **13 columns** (`5` chunk columns + the object table's `8` columns) | Top-level `uri` |
| **3. `ObjectRef` subquery** | `AI.CHUNK_DOCUMENT((SELECT doc_id, OBJ.MAKE_REF(uri) AS ref FROM ...), chunk_size => 500)` | **`5 + N` columns** (`5` chunk columns + the `N` columns projected by the subquery) | `ref.uri` unless the subquery also projected `uri` explicitly |
| **4. Pre-parsed `parsed_document` table / subquery** | `AI.CHUNK_DOCUMENT(TABLE \`PROJECT_ID.DATASET.parsed_docs\`, chunk_size => 250)` *(where `parsed_document` holds `raw-docai` JSON from `AI.PARSE_DOCUMENT`)* | **`5 + N` columns** (`5` chunk columns + all `N` columns of the input table/subquery, including `parsed_document`) | Any passthrough `uri` / `doc_id` column included alongside `parsed_document` |

> **GOTCHA — Subquery `ref` or `parsed_document` column binding & schema requirement:** The `TABLE` / `(query_statement)` forms bind their input column **by exact column name (`ref` or `parsed_document`)**, not by column position (`AI.CHUNK_DOCUMENT expects the input table to have a column named 'ref' or 'parsed_document', but both are missing.`). When chaining [`AI.PARSE_DOCUMENT`](#aiparse_document) into `AI.CHUNK_DOCUMENT`, you **must** pass `options => JSON '{"schema": "raw-docai"}'` to `AI.PARSE_DOCUMENT`; passing default `layout-v1` JSON into `AI.CHUNK_DOCUMENT` returns per-row `status = 'INVALID_ARGUMENT: Unsupported document schema: layout-v1'` with `content = NULL`. When `(query_statement)` selects only `OBJ.MAKE_REF(uri) AS ref`, `AI.CHUNK_DOCUMENT` returns **6 columns** (`chunk_id`, `content`, `start_page`, `end_page`, `status`, `ref`) with **no top-level `uri` column** — read `ref.uri` or project `uri` alongside `ref` in the subquery.

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

-- 3. "Parse once, chunk many times": re-chunk a pre-parsed raw-docai JSON column
SELECT doc_id, chunk_id, start_page, end_page, content
FROM AI.CHUNK_DOCUMENT(
  (
    SELECT
      doc_id,
      AI.PARSE_DOCUMENT(
        OBJ.MAKE_REF(gcs_uri),
        options => JSON '{"schema": "raw-docai"}'
      ) AS parsed_document
    FROM `your-gcp-project-id.DATASET_ID.document_catalog`
  ),
  chunk_size => 250
)
WHERE status = '';
```

**Supported file types and size limits:**
- **Supported formats:** PDF (`.pdf`), HTML (`.html`), Word OOXML (`.docx`), PowerPoint OOXML (`.pptx`), and Excel OOXML (`.xlsx`, `.xlsm`).
- **Unsupported formats:** Plain text (`.txt`), Markdown (`.md`), and standalone raster images (`.png`, `.jpg`, `.jpeg`, `.gif`, `.tiff`, `.bmp`, `.webp`) return non-empty per-row `status` errors. Chunk `.txt`/`.md` directly in SQL or use [`ML.PROCESS_DOCUMENT`](#mlprocess_document) with an OCR/specialized processor for standalone images.
- **Size and page limits:** Up to **20 MB / 15 pages** on the synchronous Document AI path, up to **1 GB / 500 pages** on the batch PDF path, and up to **130 pages** when chaining pre-parsed output from [`AI.PARSE_DOCUMENT`](#aiparse_document).

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
- When you also need structured layout inspection (`layout-v1`) or want to test multiple `chunk_size` settings without re-paying Document AI per-page parsing fees, materialize `AI.PARSE_DOCUMENT(..., options => JSON '{"schema": "raw-docai"}') AS parsed_document` once and pass that table to `AI.CHUNK_DOCUMENT`.
- Inspect failed documents separately with `WHERE status IS NOT NULL AND status != ''` (Document AI errors) and `WHERE status IS NULL` (missing `OBJ.MAKE_REF` URIs).
- Tune `chunk_size` (`250`–`500` tokens for dense Q&A retrieval, `1000` default for broader passage context); ancestor headings are automatically prepended so small chunks retain section context.

**Locations:** Supported in the **`US`** and **`EU`** multi-regions and in US and EU single regions **excluding London (`europe-west2`) and Zurich (`europe-west6`)**.

**Pricing & Provisioned throughput:** Billed at standard Document AI Layout Parser rates (**$10 per 1,000 pages** processed) plus BigQuery query compute when reading from Cloud Storage; re-chunking an already materialized `parsed_document` JSON column incurs only BigQuery query compute. `bq-created-layout-parser` incurs zero idle fee. Subject to Document AI Layout Parser quotas rather than Vertex AI Gemini Provisioned Throughput.

**BigFrames API:** As of `bigframes 2.53.0`, there is no dedicated `bigframes.bigquery.ai.chunk_document()` wrapper; execute via `bpd.read_gbq_query("SELECT * FROM AI.CHUNK_DOCUMENT(...)")`.

---

## `ML.PROCESS_DOCUMENT`
- **Description:** Table-valued function that processes unstructured documents from an object table using the Document AI API. Sends documents stored in Cloud Storage (referenced via a BigQuery object table) to a Document AI processor and returns structured extraction results (entities, key-value pairs, parsed content) directly as BigQuery columns. For zero-DDL layout-aware RAG chunking or structured layout JSON (`layout-v1` / `raw-docai`) without `CREATE MODEL`, prefer [`AI.CHUNK_DOCUMENT`](#aichunk_document) and [`AI.PARSE_DOCUMENT`](#aiparse_document).
- **Use cases:** Invoice parsing, expense/receipt extraction, form key-value extraction, OCR text extraction on standalone images and scans, document layout analysis and chunking (when custom `PROCESS_OPTIONS` are needed), bank statement parsing, W2/tax form parsing, utility bill parsing, pay slip parsing, US passport and driver license parsing, identity document proofing, custom document classification, custom document splitting, document summarization.
- [documentation](https://cloud.google.com/bigquery/docs/reference/standard-sql/bigqueryml-syntax-process-document)
- **Type:** Table-valued function (returns a table)

**Syntax:**
```sql
SELECT *
FROM ML.PROCESS_DOCUMENT(
  MODEL `PROJECT_ID.DATASET.MODEL`,
  { TABLE `PROJECT_ID.DATASET.OBJECT_TABLE` | (QUERY_STATEMENT) }
  [, PROCESS_OPTIONS => (JSON 'PROCESS_OPTIONS')]
);
```

**Model creation (prerequisite):**
```sql
CREATE OR REPLACE MODEL `PROJECT_ID.DATASET_ID.MODEL_NAME`
REMOTE WITH CONNECTION {DEFAULT | `PROJECT_ID.REGION.CONNECTION_ID`}
OPTIONS (
  REMOTE_SERVICE_TYPE = 'CLOUD_AI_DOCUMENT_V1',
  DOCUMENT_PROCESSOR = 'PROCESSOR_ID'
);
```

**Inputs:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `MODEL` | Model reference | Required | -- | Fully-qualified name of a remote model with `REMOTE_SERVICE_TYPE = 'CLOUD_AI_DOCUMENT_V1'`. |
| `TABLE` / `(QUERY_STATEMENT)` | Table or subquery | Required | -- | Object table reference or a `SELECT` subquery over the object table. Subquery cannot use `JOIN` or rename columns with aliases. Must include `uri` and `content_type` columns. |
| `PROCESS_OPTIONS` | JSON (named parameter) | Optional | -- | A `ProcessOptions` resource in JSON format. Configures processing options like OCR config, layout parser chunking, page selection. |

**PROCESS_OPTIONS details:**

| Field | Applicable To | Description |
|-------|---------------|-------------|
| `ocrConfig.hints.languageHints[]` | OCR, Form Parser | BCP-47 language codes. Auto-detection if not specified. |
| `ocrConfig.enableNativePdfParsing` | OCR, Form Parser | Better extraction for PDFs with existing text. |
| `ocrConfig.enableImageQualityScores` | OCR, Form Parser | Returns quality scores. Adds latency. |
| `ocrConfig.premiumFeatures.enableSelectionMarkDetection` | OCR 2.0+ | Enable checkbox detection. |
| `ocrConfig.premiumFeatures.computeStyleInfo` | OCR, Form Parser | Enable font identification and style info. |
| `ocrConfig.premiumFeatures.enableMathOcr` | OCR, Form Parser | Extract LaTeX math formulas. |
| `layoutConfig.chunkingConfig.chunkSize` | Layout Parser | Chunk size for splitting documents. |
| `layoutConfig.chunkingConfig.includeAncestorHeadings` | Layout Parser | Include ancestor headings when splitting. |
| `layoutConfig.returnImages` | Layout Parser | Include images in response. |
| `layoutConfig.returnBoundingBoxes` | Layout Parser | Include bounding boxes. |
| `individualPageSelector.pages[]` | All | 1-indexed list of specific pages to process. |
| `fromStart` | All | Only process this many pages from the start. |
| `fromEnd` | All | Only process this many pages from the end. |

Note: `individualPageSelector`, `fromStart`, and `fromEnd` are a union field — only one can be specified. Setting `ocrConfig` on a non-OCR processor or `layoutConfig` on a non-Layout Parser processor returns an error.

**Outputs:**

| Column | Type | Description |
|--------|------|-------------|
| `ml_process_document_result` | JSON | Entities returned by the Document AI API (confidence scores, mention text, page anchors, bounding polygons, properties). |
| `ml_process_document_status` | STRING | API response status. Empty if successful. Contains error messages (e.g., `RESOURCE EXHAUSTED`) if processing failed. |
| *(processor-specific fields)* | *(varies)* | Fields specific to the processor (e.g., invoice parser returns `invoice_type`, `currency`, `total_amount`). Visible in the model's Schema tab under Labels. |
| *(object table columns)* | *(varies)* | All columns from the input object table or query are passed through (e.g., `uri`, `content_type`). |

**Supported Document AI processors:**

| Category | Processor | Type ID |
|----------|-----------|---------|
| Digitize Text | Enterprise Document OCR | `OCR_PROCESSOR` |
| Extract (General) | Custom Extractor | `CUSTOM_EXTRACTION_PROCESSOR` |
| Extract (General) | Form Parser | `FORM_PARSER_PROCESSOR` |
| Extract (General) | Layout Parser | `LAYOUT_PARSER_PROCESSOR` |
| Extract (Pretrained) | Bank Statement Parser | `BANK_STATEMENT_PROCESSOR` |
| Extract (Pretrained) | W2 Parser | `FORM_W2_PROCESSOR` |
| Extract (Pretrained) | US Passport Parser | `US_PASSPORT_PROCESSOR` |
| Extract (Pretrained) | Utility Parser | `UTILITY_PROCESSOR` |
| Extract (Pretrained) | Identity Document Proofing | `ID_PROOFING_PROCESSOR` |
| Extract (Pretrained) | Pay Slip Parser | `PAYSTUB_PROCESSOR` |
| Extract (Pretrained) | US Driver License Parser | `US_DRIVER_LICENSE_PROCESSOR` |
| Extract (Pretrained) | Expense Parser | `EXPENSE_PROCESSOR` |
| Extract (Pretrained) | Invoice Parser | `INVOICE_PROCESSOR` |
| Classify | Custom Classifier | `CUSTOM_CLASSIFICATION_PROCESSOR` |
| Split | Custom Splitter | `CUSTOM_SPLITTING_PROCESSOR` |
| Summarize | Summarizer | `SUMMARY_PROCESSOR` |

**Supported file types:**

| Format | Extensions | MIME Type |
|--------|-----------|-----------|
| PDF | `.pdf` | `application/pdf` |
| GIF | `.gif` | `image/gif` |
| TIFF | `.tiff`, `.tif` | `image/tiff` |
| JPEG | `.jpg`, `.jpeg` | `image/jpeg` |
| PNG | `.png` | `image/png` |
| BMP | `.bmp` | `image/bmp` |
| WebP | `.webp` | `image/webp` |
| HTML | `.html` | `text/html` (Layout Parser only) |
| Word OOXML | `.docx` | `application/vnd.openxmlformats-officedocument.wordprocessingml.document` (Layout Parser only) |
| PowerPoint OOXML | `.pptx` | `application/vnd.openxmlformats-officedocument.presentationml.presentation` (Layout Parser only) |
| Excel OOXML | `.xlsx` | `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet` (Layout Parser only) |

**Best practices:**
- Filter documents with `WHERE`/`LIMIT` in a subquery rather than processing the entire object table.
- Use `CREATE TABLE ... AS SELECT` to persist results and avoid re-processing.
- Handle `RESOURCE_EXHAUSTED` errors with BigQuery remote inference SQL scripts or the Dataform package for retry-until-complete iteration.
- Select only the processor-specific columns you need rather than `SELECT *`.
- Minimum 200 dpi for document scans; 300 dpi or higher recommended.

**Limitations:**
- Maximum **130 pages per document**. Rows with larger documents return an error.
- **120-second timeout per request.** Documents that take longer to process will fail.
- **Requests are processed in batches of 10.**
- Custom Splitter only supports PDF, TIFF, TIF, and GIF.
- See [Cloud AI service functions quotas](https://cloud.google.com/bigquery/quotas#cloud_ai_service_functions) for current rate limits.
- Some rows may show `RESOURCE EXHAUSTED` errors after job success — BigQuery retries internally, but parallel batch queries can exceed quota limits.

**Locations:** Models can only be created in the **US** and **EU** multi-regions. The dataset, connection, and Document AI processor must all be in the same region.

**Provisioned throughput:** Not specified. Subject to Document AI API quotas.

**BigFrames API:** No direct equivalent. Use `%%bigquery` magics or `session.read_gbq_query()` to execute ML.PROCESS_DOCUMENT SQL from BigFrames.

---

## `AI.PARSE_DOCUMENT`
- **Description:** Scalar function that parses a document in Cloud Storage (or Google Drive via `ObjectRef`) into structured layout JSON using an auto-provisioned Document AI Layout Parser processor (`bq-created-layout-parser`) — requiring zero `CREATE MODEL` DDL and zero manual processor setup. Returns either flat reading-order blocks (`layout-v1`, default) with HTML tables and normalized bounding boxes, or the full nested Document AI layout tree (`raw-docai`) that can be chained directly into [`AI.CHUNK_DOCUMENT`](#aichunk_document) as `parsed_document`.
- **Use cases:** Extracting structured reading-order layout blocks (`title`, `heading`, `text`, `table` HTML, `list_item`, `image`, `page_header`, `page_footer`) with page numbers and `[min_y, min_x, max_y, max_x]` bounding boxes; pulling HTML tables out of PDFs, Word documents, PowerPoint decks, Excel workbooks, or HTML pages; and "parse once, chunk many times" pipelines where `AI.PARSE_DOCUMENT(..., options => JSON '{"schema": "raw-docai"}') AS parsed_document` is materialized once and re-chunked at multiple `chunk_size` values via [`AI.CHUNK_DOCUMENT`](#aichunk_document).
- [documentation](https://docs.cloud.google.com/bigquery/docs/reference/standard-sql/bigqueryml-syntax-ai-parse-document) · [notebook](../functions/ai_parse_document/ai_parse_document.ipynb) · [sql](../functions/ai_parse_document/ai_parse_document.sql)
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
| `options` | `JSON` (named parameter) | Optional | `JSON '{"schema": "layout-v1"}'` | Output JSON schema selector: `JSON '{"schema": "layout-v1"}'` (default flat reading-order blocks) or `JSON '{"schema": "raw-docai"}'` (full nested Document AI `DocumentLayoutBlock` tree, required when chaining into [`AI.CHUNK_DOCUMENT`](#aichunk_document)). Passing an unknown schema name raises an analysis-time `400 Unsupported document parsing schema` error. |

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
- **Unsupported formats:** Plain text (`.txt`), Markdown (`.md`), and standalone raster images (`.png`, `.jpg`, `.tiff`, etc.) return a per-row `INVALID_ARGUMENT` entry in `$.errors`. Use [`ML.PROCESS_DOCUMENT`](#mlprocess_document) with an OCR or specialized processor for standalone images.
- **Page limit:** Maximum **130 pages per document**. Documents exceeding 130 pages return a per-row `INVALID_ARGUMENT` in `$.errors` (for PDFs up to 500 pages that only need RAG chunks, call [`AI.CHUNK_DOCUMENT`](#aichunk_document) directly on the `'gs://...'` URI or `ObjectRef`).

**Auto-provisioned processor, IAM & VPC-SC:**
- Uses the same auto-provisioned `bq-created-layout-parser` Document AI Layout Parser processor ($0 idle fee), `documentai.googleapis.com` API, and IAM roles (`roles/documentai.editor` on first call in a region, `roles/documentai.viewer` thereafter, plus `roles/storage.objectViewer`) as [`AI.CHUNK_DOCUMENT`](#aichunk_document).
- **VPC Service Controls (VPC-SC):** Inside a VPC-SC perimeter, pass a direct `'gs://...'` URI string or 1-argument `OBJ.MAKE_REF(uri)` under end-user credentials rather than a connection-backed `ObjectRef` or object table.

**Locations:** Supported in the **`US`** and **`EU`** multi-regions and in US and EU single regions **excluding London (`europe-west2`) and Zurich (`europe-west6`)**.

**Pricing & Provisioned throughput:** Billed at standard Document AI Layout Parser rates (**$10 per 1,000 pages** processed) plus BigQuery query compute; `bq-created-layout-parser` incurs zero idle fee.

**BigFrames API:** As of `bigframes 2.53.0`, there is no dedicated `bigframes.bigquery.ai.parse_document()` wrapper; execute via `bpd.read_gbq_query("SELECT AI.PARSE_DOCUMENT(...) AS parsed_doc ...")`.
