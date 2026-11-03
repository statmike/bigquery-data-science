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

These functions process unstructured documents (PDFs, Office files, HTML, images, forms, invoices) using Document AI processors, returning layout-aware chunks or structured entity extractions directly as BigQuery columns.

| Capability | [`AI.CHUNK_DOCUMENT`](#aichunk_document) | [`ML.PROCESS_DOCUMENT`](#mlprocess_document) |
|------------|------------------------------------------|----------------------------------------------|
| **Release status** | GA | GA |
| **Prerequisite DDL** | None — auto-provisions `bq-created-layout-parser` on first run | `CREATE MODEL ... REMOTE_SERVICE_TYPE = 'CLOUD_AI_DOCUMENT_V1'` + pre-created Document AI processor |
| **Processor coverage** | Document AI Layout Parser only (layout-aware RAG chunking) | All 16 Document AI processor types (Invoice, Expense, Form, OCR, W2, Custom, Layout Parser, etc.) |
| **Input forms** | `'gs://...'` URI/wildcard literal, `TABLE object_table`, or `(SELECT ... ObjectRef)` subquery | `TABLE object_table` or constrained `SELECT` subquery over an object table |
| **Max document size** | Up to **500 pages / 1 GB** (batch PDF path); **15 pages / 20 MB** (sync path) | Up to **130 pages** per document (`120s` per-request timeout) |
| **Supported formats** | PDF, HTML, DOCX, PPTX, XLSX, XLSM *(no standalone raster images, `.txt`, or `.md`)* | PDF, GIF, TIFF, JPEG, PNG, BMP, WebP, plus HTML, DOCX, PPTX, XLSX (Layout Parser) |

> **Historical note:** [`AI.PARSE_DOCUMENT`](#aiparse_document) (Preview) was taken offline on 2026-06-01 and its documentation was withdrawn by 2026-09-01; [`AI.CHUNK_DOCUMENT`](#aichunk_document) is its GA zero-DDL replacement for layout-aware document chunking.

---

## `AI.CHUNK_DOCUMENT`
- **Description:** Table-valued function that splits unstructured documents in Cloud Storage into layout-aware text chunks using an auto-provisioned Document AI Layout Parser processor (`bq-created-layout-parser`) — requiring zero `CREATE MODEL` DDL and zero manual Document AI processor setup.
- **Use cases:** Layout-aware chunking of PDFs, Word documents, PowerPoint decks, Excel workbooks, and HTML pages for RAG pipelines (`AI.CHUNK_DOCUMENT` -> `AI.EMBED` -> `VECTOR_SEARCH` / `AI.SEARCH`), section-preserving document ingestion with ancestor headings, ad-hoc single-URI or wildcard GCS document parsing without creating an object table.
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
- **Unsupported formats:** Plain text (`.txt`), Markdown (`.md`), and standalone raster images (`.png`, `.jpg`, `.jpeg`, `.gif`, `.tiff`, `.bmp`, `.webp`) return non-empty per-row `status` errors. Chunk `.txt`/`.md` directly in SQL or use [`ML.PROCESS_DOCUMENT`](#mlprocess_document) with an OCR/specialized processor for standalone images.
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

## `ML.PROCESS_DOCUMENT`
- **Description:** Table-valued function that processes unstructured documents from an object table using the Document AI API. Sends documents stored in Cloud Storage (referenced via a BigQuery object table) to a Document AI processor and returns structured extraction results (entities, key-value pairs, parsed content) directly as BigQuery columns. For zero-DDL layout-aware RAG chunking of PDFs (up to 500 pages), HTML, DOCX, PPTX, and XLSX/XLSM without `CREATE MODEL`, prefer [`AI.CHUNK_DOCUMENT`](#aichunk_document).
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
- **⚠️ Status (as of 2026-09-01): OFFLINE, and reference documentation WITHDRAWN — superseded by GA [`AI.CHUNK_DOCUMENT`](#aichunk_document).** The function (Preview) was taken offline by Google for revision on 2026-06-01 and does not execute; its reference page `.../bigqueryml-syntax-ai-parse-document` returns **HTTP 404**.
  - **GA replacement:** Use [`AI.CHUNK_DOCUMENT`](#aichunk_document) for zero-DDL layout-aware chunking of PDFs, HTML, DOCX, PPTX, and XLSX/XLSM — it removes both `CREATE MODEL` and manual Document AI processor setup by auto-provisioning `bq-created-layout-parser`. Use [`ML.PROCESS_DOCUMENT`](#mlprocess_document) when you need specialized Document AI processors (invoice, receipt, form, OCR on standalone images, custom extractors) or custom `PROCESS_OPTIONS`.
  - **Affected content:** `functions/ai_parse_document/` carries an archival retirement banner. Its committed outputs are a historical record of the function before 2026-06-01, not current behavior. Do not re-run it. Documentation below is retained from the last published version of the page as an archived snapshot.
- **Description:** (Preview — retired) Table-valued function that parsed documents using the Document AI Layout Parser without a `CREATE MODEL` step.
- **Use cases:** Historical reference only — migrate RAG chunking to [`AI.CHUNK_DOCUMENT`](#aichunk_document).
- [documentation](https://docs.cloud.google.com/bigquery/docs/reference/standard-sql/bigqueryml-syntax-ai-parse-document) — **dead link (HTTP 404 as of 2026-09-01)**, retained as an archival record
- **Type:** Table-valued function (returns a table) — Preview (⚠️ offline)

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

**Relationship to `AI.CHUNK_DOCUMENT` and `ML.PROCESS_DOCUMENT`:** [`AI.CHUNK_DOCUMENT`](#aichunk_document) supersedes `AI.PARSE_DOCUMENT` at GA by eliminating manual Document AI processor creation (`endpoint` is replaced by auto-provisioned `bq-created-layout-parser`) and adding a per-row `status` column plus direct `'gs://...'` string inputs up to 500 PDF pages. Use [`ML.PROCESS_DOCUMENT`](#mlprocess_document) when you need specialized Document AI processors (invoice, form, OCR on images, custom) or fine-grained `PROCESS_OPTIONS`.
