# `ML.PROCESS_DOCUMENT`

> **Source:** [`bigquery-ai/reference/document-processing.md#mlprocess_document`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ai/reference/document-processing.md#mlprocess_document)

- **Description:** Table-valued function that processes unstructured documents from an object table using the Document AI API. Sends documents stored in Cloud Storage (referenced via a BigQuery object table) to a Document AI processor and returns structured extraction results (entities, key-value pairs, parsed content) directly as BigQuery columns.
- **Use cases:** Invoice parsing, expense/receipt extraction, form key-value extraction, OCR text extraction, document layout analysis and chunking (for RAG pipelines), bank statement parsing, W2/tax form parsing, utility bill parsing, pay slip parsing, US passport and driver license parsing, identity document proofing, custom document classification, custom document splitting, document summarization.
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
