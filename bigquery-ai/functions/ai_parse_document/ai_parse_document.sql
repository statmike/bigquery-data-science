-- ============================================================================
-- AI.PARSE_DOCUMENT — Progressive SQL Examples
-- ============================================================================
-- Scalar function (GA) that parses unstructured documents in Cloud Storage
-- (or Google Drive via ObjectRef) — PDF, HTML, DOCX, PPTX, XLSX, XLSM — into
-- structured JSON (`layout-v1` reading-order blocks or the `raw-docai`
-- Document AI layout tree) using an auto-provisioned Document AI Layout Parser
-- processor (`bq-created-layout-parser`, $0 idle fee, up to 130 pages).
--
-- Replace `your-gcp-project-id` with your Google Cloud project ID.
-- For full setup (Document AI API, connection IAM grants, and staged sample
-- files), see ai_parse_document.ipynb or ../../setup/.
--
-- Prerequisites:
--   1. Enable API: documentai.googleapis.com
--   2. First call in a project requires `roles/documentai.editor` on the
--      authenticating principal (EUC or connection SA) so BigQuery can create
--      `bq-created-layout-parser`; subsequent calls require only
--      `roles/documentai.viewer`, plus `roles/storage.objectViewer`.
--   3. Supported in US/EU multi-regions and US/EU single regions EXCEPT
--      `europe-west2` (London) and `europe-west6` (Zurich).
--   4. Inside VPC Service Controls, use EUC (`'gs://...'` literal or 1-arg
--      `OBJ.MAKE_REF(uri)`); delegated `ObjectRef` URLs are rejected by VPC-SC.


-- ============================================================================
-- Optional Setup: Object Table over PDFs in Cloud Storage
-- ============================================================================

-- CREATE SCHEMA IF NOT EXISTS `your-gcp-project-id.bq_ai_functions`
-- OPTIONS (location = 'US');

-- CREATE OR REPLACE EXTERNAL TABLE `your-gcp-project-id.bq_ai_functions.ai_parse_document_docs`
-- WITH CONNECTION `your-gcp-project-id.US.bq_ai_functions`
-- OPTIONS (
--   object_metadata = 'SIMPLE',
--   uris = ['gs://your-gcp-project-id/bq_ai_functions/ai_parse_document/docs/*.pdf']
-- );


-- ============================================================================
-- Example 1: Simplest starter call — public GCS URI with EUC & layout-v1
-- ============================================================================
-- By default (`options => JSON '{"schema": "layout-v1"}'`), AI.PARSE_DOCUMENT
-- returns:
--   {
--     "metadata": {"schema": "layout-v1"},
--     "blocks": [
--       {"id": 0, "type": "heading", "page_number": 1, "bbox": [...], "content": "..."},
--       ...
--     ]
--   }
-- (and an "errors" array only if parsing fails).

WITH Parsed AS (
  SELECT
    AI.PARSE_DOCUMENT(
      'gs://cloud-samples-data/bigquery/tutorials/cymbal-pets/documents/crittercuisine_5000_user_manual.pdf'
    ) AS parsed_doc
)
SELECT
  JSON_VALUE(parsed_doc.metadata.schema) AS schema_version,
  ARRAY_LENGTH(JSON_QUERY_ARRAY(parsed_doc.blocks)) AS block_count,
  JSON_QUERY(parsed_doc, '$.errors') AS errors_field,
  JSON_QUERY_ARRAY(parsed_doc.blocks)[OFFSET(0)] AS first_block
FROM Parsed;


-- ============================================================================
-- Example 2: Flattening `blocks` into relational SQL rows with UNNEST
-- ============================================================================
-- Extract typed block columns (`block_id`, `block_type`, `page_number`,
-- `bbox`, `content`). Tables are returned with `block_type = 'table'` and
-- serialized as HTML `<table>...</table>` strings in `content`.

WITH Parsed AS (
  SELECT
    AI.PARSE_DOCUMENT(
      'gs://your-gcp-project-id/bq_ai_functions/ai_parse_document/docs/handbook_multipage.pdf',
      connection_id => 'your-gcp-project-id.US.bq_ai_functions'
    ) AS parsed_doc
)
SELECT
  INT64(block.id) AS block_id,
  JSON_VALUE(block.type) AS block_type,
  INT64(block.page_number) AS page_number,
  TO_JSON_STRING(block.bbox) AS bbox,
  JSON_VALUE(block.content) AS content
FROM Parsed,
UNNEST(JSON_QUERY_ARRAY(parsed_doc.blocks)) AS block
ORDER BY block_id;


-- ============================================================================
-- Example 3: All 4 input & authentication shapes
-- ============================================================================
-- Note: Google Drive files are supported when passed as an `ObjectRef` value
-- (passing a Google Drive URI directly as a STRING is not supported).

-- Shape A: 'gs://...' URI string with explicit `connection_id`
SELECT
  'Shape A: URI + connection_id' AS input_shape,
  AI.PARSE_DOCUMENT(
    document => 'gs://your-gcp-project-id/bq_ai_functions/ai_parse_document/docs/invoice_001.pdf',
    connection_id => 'your-gcp-project-id.US.bq_ai_functions'
  ) AS parsed_doc;

-- Shape B: Inline `OBJ.MAKE_REF(uri, connection_id)` (no Object Table needed)
SELECT
  'Shape B: Inline OBJ.MAKE_REF' AS input_shape,
  AI.PARSE_DOCUMENT(
    OBJ.MAKE_REF(
      'gs://your-gcp-project-id/bq_ai_functions/ai_parse_document/docs/invoice_001.pdf',
      'your-gcp-project-id.US.bq_ai_functions'
    )
  ) AS parsed_doc;

-- Shape C: Multi-document folder parsing via `FROM OBJ.LIST(wildcard, conn)`
SELECT
  ref.uri AS uri,
  ARRAY_LENGTH(JSON_QUERY_ARRAY(parsed_doc.blocks)) AS block_count
FROM (
  SELECT
    ref,
    AI.PARSE_DOCUMENT(ref) AS parsed_doc
  FROM OBJ.LIST(
    'gs://your-gcp-project-id/bq_ai_functions/ai_parse_document/docs/*.pdf',
    'your-gcp-project-id.US.bq_ai_functions'
  )
)
ORDER BY uri;

-- Shape D: Querying an Object Table (`FROM project.dataset.object_table`)
SELECT
  uri,
  content_type,
  size,
  ARRAY_LENGTH(JSON_QUERY_ARRAY(parsed_doc.blocks)) AS block_count
FROM (
  SELECT
    uri,
    content_type,
    size,
    AI.PARSE_DOCUMENT(ref) AS parsed_doc
  FROM `your-gcp-project-id.bq_ai_functions.ai_parse_document_docs`
)
ORDER BY uri;


-- ============================================================================
-- Example 4: Output schemas — `layout-v1` (default) vs `raw-docai`
-- ============================================================================
-- `layout-v1` returns a flat reading-order `blocks` array (`id`, `type`,
-- `page_number`, `bbox`, `content`).
-- `raw-docai` returns the nested Document AI `DocumentLayoutBlock` tree in
-- camelCase (`blockId`, `pageSpan`, `textBlock.blocks`, `tableBlock`, etc.).

WITH BothSchemas AS (
  SELECT
    AI.PARSE_DOCUMENT(
      'gs://your-gcp-project-id/bq_ai_functions/ai_parse_document/docs/handbook_multipage.pdf',
      connection_id => 'your-gcp-project-id.US.bq_ai_functions',
      options => JSON '{"schema": "layout-v1"}'
    ) AS doc_layout_v1,
    AI.PARSE_DOCUMENT(
      'gs://your-gcp-project-id/bq_ai_functions/ai_parse_document/docs/handbook_multipage.pdf',
      connection_id => 'your-gcp-project-id.US.bq_ai_functions',
      options => JSON '{"schema": "raw-docai"}'
    ) AS doc_raw_docai
)
SELECT
  JSON_VALUE(doc_layout_v1.metadata.schema) AS layout_v1_schema,
  ARRAY_LENGTH(JSON_QUERY_ARRAY(doc_layout_v1.blocks)) AS layout_v1_flat_blocks,
  JSON_VALUE(doc_raw_docai.metadata.schema) AS raw_docai_schema,
  ARRAY_LENGTH(JSON_QUERY_ARRAY(doc_raw_docai.blocks)) AS raw_docai_root_blocks,
  ARRAY_LENGTH(JSON_QUERY_ARRAY(doc_raw_docai.blocks[0].textBlock.blocks)) AS raw_docai_root0_children,
  JSON_VALUE(doc_raw_docai.blocks[0].textBlock.type) AS raw_docai_first_block_type,
  JSON_VALUE(doc_raw_docai.blocks[0].textBlock.text) AS raw_docai_first_block_text
FROM BothSchemas;

-- Negative boundary probe (commented out because it raises an analysis-time 400 error):
-- SELECT AI.PARSE_DOCUMENT(
--   'gs://your-gcp-project-id/bq_ai_functions/ai_parse_document/docs/invoice_001.pdf',
--   options => JSON '{"schema": "unknown"}'
-- );


-- ============================================================================
-- Example 5: Chaining `AI.PARSE_DOCUMENT` (`raw-docai`) into `AI.CHUNK_DOCUMENT`
--            ("Parse Once, Chunk Many Times")
-- ============================================================================
-- Pass `options => JSON '{"schema": "raw-docai"}'` aliased `AS parsed_document`
-- into `AI.CHUNK_DOCUMENT` to experiment with multiple `chunk_size` settings
-- without re-invoking Document AI.

WITH ParsedOnce AS (
  SELECT
    'DOC-RUNBOOK' AS doc_id,
    AI.PARSE_DOCUMENT(
      'gs://your-gcp-project-id/bq_ai_functions/ai_parse_document/docs/handbook_multipage.pdf',
      connection_id => 'your-gcp-project-id.US.bq_ai_functions',
      options => JSON '{"schema": "raw-docai"}'
    ) AS parsed_document
),
FineChunks AS (
  SELECT 150 AS target_tokens, doc_id, chunk_id, start_page, end_page, content
  FROM AI.CHUNK_DOCUMENT((SELECT * FROM ParsedOnce), chunk_size => 150)
  WHERE status = ''
),
CoarseChunks AS (
  SELECT 800 AS target_tokens, doc_id, chunk_id, start_page, end_page, content
  FROM AI.CHUNK_DOCUMENT((SELECT * FROM ParsedOnce), chunk_size => 800)
  WHERE status = ''
),
Combined AS (
  SELECT * FROM FineChunks
  UNION ALL
  SELECT * FROM CoarseChunks
)
SELECT
  doc_id,
  target_tokens,
  COUNT(*) AS chunk_count,
  MIN(CHAR_LENGTH(content)) AS min_chars,
  CAST(ROUND(AVG(CHAR_LENGTH(content))) AS INT64) AS avg_chars,
  MAX(CHAR_LENGTH(content)) AS max_chars
FROM Combined
GROUP BY doc_id, target_tokens
ORDER BY target_tokens;

-- Gotcha probe (commented out: passing default `layout-v1` into AI.CHUNK_DOCUMENT
-- returns per-row `status = 'INVALID_ARGUMENT: Unsupported document schema: layout-v1'`):
-- SELECT doc_id, chunk_id, content, status
-- FROM AI.CHUNK_DOCUMENT(
--   (
--     SELECT
--       'DOC-INV-001' AS doc_id,
--       AI.PARSE_DOCUMENT(
--         'gs://your-gcp-project-id/bq_ai_functions/ai_parse_document/docs/invoice_001.pdf',
--         connection_id => 'your-gcp-project-id.US.bq_ai_functions'
--       ) AS parsed_document
--   ),
--   chunk_size => 300
-- );


-- ============================================================================
-- Example 6: Multi-format inputs (.html, .docx, .xlsx) & 3-way error contract
-- ============================================================================
-- 1. NULL input                -> returns SQL NULL
-- 2. Valid supported document  -> `blocks` populated, `errors` absent (NULL)
-- 3. Unsupported MIME or 404   -> `blocks: []`, `errors: [{code, message}]`
-- Always filter valid documents with:
--   WHERE parsed_doc IS NOT NULL AND JSON_QUERY(parsed_doc, '$.errors') IS NULL

WITH MixedInputs AS (
  SELECT '0_null_input'       AS input_label, CAST(NULL AS STRING) AS uri
  UNION ALL
  SELECT '1_html_valid'       AS input_label, 'gs://your-gcp-project-id/bq_ai_functions/ai_parse_document/formats/release_notes.html'    AS uri
  UNION ALL
  SELECT '2_docx_valid'       AS input_label, 'gs://your-gcp-project-id/bq_ai_functions/ai_parse_document/formats/vendor_policy.docx'    AS uri
  UNION ALL
  SELECT '3_xlsx_valid'       AS input_label, 'gs://your-gcp-project-id/bq_ai_functions/ai_parse_document/formats/slo_matrix.xlsx'       AS uri
  UNION ALL
  SELECT '4_txt_unsupported'  AS input_label, 'gs://your-gcp-project-id/bq_ai_functions/ai_parse_document/unsupported/plain_note.txt'    AS uri
  UNION ALL
  SELECT '5_pdf_missing_blob' AS input_label, 'gs://your-gcp-project-id/bq_ai_functions/ai_parse_document/docs/missing_document_404.pdf' AS uri
),
Parsed AS (
  SELECT
    input_label,
    AI.PARSE_DOCUMENT(
      uri,
      connection_id => 'your-gcp-project-id.US.bq_ai_functions'
    ) AS parsed_doc
  FROM MixedInputs
)
SELECT
  input_label,
  CASE
    WHEN parsed_doc IS NULL THEN 'sql_null'
    WHEN JSON_QUERY(parsed_doc, '$.errors') IS NULL THEN 'valid_document'
    ELSE 'document_error'
  END AS row_outcome,
  ARRAY_LENGTH(JSON_QUERY_ARRAY(parsed_doc.blocks)) AS block_count,
  JSON_VALUE(parsed_doc.errors[0].code) AS error_code,
  JSON_VALUE(parsed_doc.errors[0].message) AS error_message,
  SUBSTR(JSON_VALUE(parsed_doc.blocks[0].content), 1, 90) AS first_block_preview
FROM Parsed
ORDER BY input_label;


-- ============================================================================
-- Example 7: Side-by-side comparison with AI.CHUNK_DOCUMENT and AI.GENERATE
-- ============================================================================

-- 1) AI.PARSE_DOCUMENT: element-level layout blocks (HTML tables & bboxes)
WITH Parsed AS (
  SELECT
    AI.PARSE_DOCUMENT(
      'gs://your-gcp-project-id/bq_ai_functions/ai_parse_document/docs/invoice_001.pdf',
      connection_id => 'your-gcp-project-id.US.bq_ai_functions'
    ) AS parsed_doc
)
SELECT
  INT64(block.id) AS block_id,
  JSON_VALUE(block.type) AS block_type,
  INT64(block.page_number) AS page_number,
  TO_JSON_STRING(block.bbox) AS bbox,
  JSON_VALUE(block.content) AS content
FROM Parsed,
UNNEST(JSON_QUERY_ARRAY(parsed_doc.blocks)) AS block
ORDER BY block_id;

-- 2) AI.CHUNK_DOCUMENT: token-bounded RAG chunks
SELECT
  chunk_id,
  start_page,
  end_page,
  content
FROM AI.CHUNK_DOCUMENT(
  'gs://your-gcp-project-id/bq_ai_functions/ai_parse_document/docs/invoice_001.pdf',
  connection_id => 'your-gcp-project-id.US.bq_ai_functions',
  chunk_size => 500
)
WHERE status = ''
ORDER BY chunk_id;

-- 3) Multimodal AI.GENERATE: single-pass structured extraction
SELECT
  extracted.vendor,
  extracted.invoice_number,
  extracted.total_due,
  extracted.summary
FROM (
  SELECT
    AI.GENERATE(
      (
        'Extract the supplier name, invoice number, total amount due, and a one-sentence summary from this invoice: ',
        OBJ.MAKE_REF(
          'gs://your-gcp-project-id/bq_ai_functions/ai_parse_document/docs/invoice_001.pdf',
          'your-gcp-project-id.US.bq_ai_functions'
        )
      ),
      connection_id => 'your-gcp-project-id.US.bq_ai_functions',
      endpoint => 'gemini-3.8-flash',
      output_schema => 'vendor STRING, invoice_number STRING, total_due FLOAT64, summary STRING'
    ) AS extracted
);


-- ============================================================================
-- Cleanup (uncomment to drop the Object Table)
-- ============================================================================

-- DROP EXTERNAL TABLE IF EXISTS `your-gcp-project-id.bq_ai_functions.ai_parse_document_docs`;
