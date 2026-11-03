-- ============================================================================
-- AI.CHUNK_DOCUMENT — Progressive SQL Examples
-- ============================================================================
-- Splits unstructured documents in Cloud Storage (PDF, HTML, DOCX, PPTX,
-- XLSX, XLSM) into layout-aware, page-attributed text chunks using an
-- auto-provisioned Document AI Layout Parser processor
-- (`bq-created-layout-parser`, $0 idle fee).
--
-- Replace `your-gcp-project-id` with your Google Cloud project ID.
-- For full setup (Document AI API, connection IAM grants, and staged sample
-- files), see ai_chunk_document.ipynb or ../../setup/.
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

-- CREATE OR REPLACE EXTERNAL TABLE `your-gcp-project-id.bq_ai_functions.ai_chunk_document_docs`
-- WITH CONNECTION `your-gcp-project-id.US.bq_ai_functions`
-- OPTIONS (
--   object_metadata = 'SIMPLE',
--   uris = ['gs://your-gcp-project-id/bq_ai_functions/ai_chunk_document/docs/*.pdf']
-- );


-- ============================================================================
-- Example 1: Simplest starter call — public GCS URI with EUC (13 columns)
-- ============================================================================
-- URI literals and Object Tables return 13 columns:
--   5 chunk columns: chunk_id, start_page, end_page, content, status
--   8 object metadata columns: uri, generation, content_type, size, md5_hash,
--                              updated, metadata, ref

SELECT
  chunk_id,
  start_page,
  end_page,
  status,
  content_type,
  size,
  content
FROM AI.CHUNK_DOCUMENT(
  'gs://cloud-samples-data/bigquery/tutorials/cymbal-pets/documents/crittercuisine_5000_user_manual.pdf'
)
WHERE status = ''
ORDER BY chunk_id;


-- ============================================================================
-- Example 2: Tuning chunk granularity with `chunk_size` (1..2000 tokens)
-- ============================================================================
-- `chunk_size` is a top-level named INT64 argument (default 1000 tokens),
-- NOT an `options => JSON` bag. Ancestor headings from earlier pages are
-- prepended automatically, so deeper sections can span e.g. start_page = 1
-- through end_page = 4.

WITH
  fine AS (
    SELECT 150 AS target_tokens, *
    FROM AI.CHUNK_DOCUMENT(
      'gs://your-gcp-project-id/bq_ai_functions/ai_chunk_document/docs/handbook_multipage.pdf',
      connection_id => 'your-gcp-project-id.US.bq_ai_functions',
      chunk_size => 150
    )
    WHERE status = ''
  ),
  coarse AS (
    SELECT 1000 AS target_tokens, *
    FROM AI.CHUNK_DOCUMENT(
      'gs://your-gcp-project-id/bq_ai_functions/ai_chunk_document/docs/handbook_multipage.pdf',
      connection_id => 'your-gcp-project-id.US.bq_ai_functions',
      chunk_size => 1000
    )
    WHERE status = ''
  ),
  combined AS (
    SELECT * FROM fine
    UNION ALL
    SELECT * FROM coarse
  )
SELECT
  target_tokens,
  COUNT(*) AS chunk_count,
  MIN(CHAR_LENGTH(content)) AS min_chars,
  CAST(ROUND(AVG(CHAR_LENGTH(content))) AS INT64) AS avg_chars,
  MAX(CHAR_LENGTH(content)) AS max_chars,
  COUNT(DISTINCT FORMAT('%d-%d', start_page, end_page)) AS distinct_page_spans
FROM combined
GROUP BY target_tokens
ORDER BY target_tokens;


-- ============================================================================
-- Example 3: All 3 input shapes — URI wildcard, Object Table, and subquery
-- ============================================================================

-- Shape A: URI wildcard literal with delegated `connection_id` (13 columns)
SELECT
  uri,
  chunk_id,
  start_page,
  end_page,
  CHAR_LENGTH(content) AS char_len
FROM AI.CHUNK_DOCUMENT(
  'gs://your-gcp-project-id/bq_ai_functions/ai_chunk_document/docs/*.pdf',
  connection_id => 'your-gcp-project-id.US.bq_ai_functions',
  chunk_size => 400
)
WHERE status = ''
ORDER BY uri, chunk_id;

-- Shape B: Object Table input (13 columns; uses the table's connection)
SELECT
  uri,
  chunk_id,
  start_page,
  end_page,
  CHAR_LENGTH(content) AS char_len
FROM AI.CHUNK_DOCUMENT(
  TABLE `your-gcp-project-id.bq_ai_functions.ai_chunk_document_docs`,
  chunk_size => 400
)
WHERE status = ''
ORDER BY uri, chunk_id;

-- Shape C: `(SELECT ... AS ref)` subquery (`5 + passthrough` columns ONLY!)
-- Note: Subquery inputs do NOT emit a top-level `uri` column unless selected
-- in the subquery. Read `ref.uri` alongside your passthrough columns (`doc_id`).
SELECT
  doc_id,
  doc_category,
  ref.uri AS source_uri,
  chunk_id,
  start_page,
  end_page,
  content
FROM AI.CHUNK_DOCUMENT(
  (
    SELECT
      doc_id,
      doc_category,
      OBJ.MAKE_REF(uri, 'your-gcp-project-id.US.bq_ai_functions') AS ref
    FROM UNNEST([
      STRUCT(
        'DOC-RUNBOOK' AS doc_id,
        'operations' AS doc_category,
        'gs://your-gcp-project-id/bq_ai_functions/ai_chunk_document/docs/handbook_multipage.pdf' AS uri
      ),
      STRUCT(
        'DOC-INV-001' AS doc_id,
        'finance' AS doc_category,
        'gs://your-gcp-project-id/bq_ai_functions/ai_chunk_document/docs/invoice_001.pdf' AS uri
      )
    ])
  ),
  chunk_size => 400
)
WHERE status = ''
ORDER BY doc_id, chunk_id;


-- ============================================================================
-- Example 4: Multi-format inputs & the 3-way per-row `status` contract
-- ============================================================================
-- Per-row `status` states:
--   1. Valid chunk              -> status = '' (empty string)
--   2. Unsupported MIME (.txt)  -> status = 'INVALID_ARGUMENT: ...'
--   3. Missing GCS object       -> status IS NULL
-- Always filter valid chunks with `WHERE status = ''`, and audit failures
-- with `WHERE status IS NULL OR status != ''`.

WITH MixedInputs AS (
  SELECT
    input_label,
    OBJ.MAKE_REF(uri, 'your-gcp-project-id.US.bq_ai_functions') AS ref
  FROM UNNEST([
    STRUCT('1_html_valid'       AS input_label, 'gs://your-gcp-project-id/bq_ai_functions/ai_chunk_document/formats/release_notes.html'    AS uri),
    STRUCT('2_docx_valid'       AS input_label, 'gs://your-gcp-project-id/bq_ai_functions/ai_chunk_document/formats/vendor_policy.docx'    AS uri),
    STRUCT('3_xlsx_valid'       AS input_label, 'gs://your-gcp-project-id/bq_ai_functions/ai_chunk_document/formats/slo_matrix.xlsx'       AS uri),
    STRUCT('4_txt_unsupported'  AS input_label, 'gs://your-gcp-project-id/bq_ai_functions/ai_chunk_document/unsupported/plain_note.txt'    AS uri),
    STRUCT('5_pdf_missing_blob' AS input_label, 'gs://your-gcp-project-id/bq_ai_functions/ai_chunk_document/docs/missing_document_404.pdf' AS uri)
  ])
)
SELECT
  input_label,
  chunk_id,
  start_page,
  end_page,
  CASE
    WHEN status = '' THEN 'valid_chunk'
    WHEN status != '' THEN 'processor_error'
    ELSE 'missing_blob_null_status'
  END AS row_outcome,
  IFNULL(status, '<NULL: missing GCS object>') AS status_display,
  SUBSTR(content, 1, 100) AS content_preview
FROM AI.CHUNK_DOCUMENT((SELECT * FROM MixedInputs), chunk_size => 500)
ORDER BY input_label, chunk_id;

-- Negative boundary probes (commented out because they raise analysis-time 400 errors):
--
-- 1) chunk_size outside [1, 2000]:
-- SELECT * FROM AI.CHUNK_DOCUMENT(
--   'gs://your-gcp-project-id/bq_ai_functions/ai_chunk_document/docs/invoice_001.pdf',
--   chunk_size => 0
-- );
-- SELECT * FROM AI.CHUNK_DOCUMENT(
--   'gs://your-gcp-project-id/bq_ai_functions/ai_chunk_document/docs/invoice_001.pdf',
--   chunk_size => 2001
-- );
--
-- 2) Subquery missing a `ref` column:
-- SELECT * FROM AI.CHUNK_DOCUMENT(
--   (SELECT 'gs://your-gcp-project-id/bq_ai_functions/ai_chunk_document/docs/invoice_001.pdf' AS document_uri)
-- );
--
-- 3) Referencing top-level `uri` on a subquery that only selected `ref`:
-- SELECT uri, content FROM AI.CHUNK_DOCUMENT(
--   (SELECT OBJ.MAKE_REF('gs://your-gcp-project-id/bq_ai_functions/ai_chunk_document/docs/invoice_001.pdf', 'your-gcp-project-id.US.bq_ai_functions') AS ref)
-- );


-- ============================================================================
-- Example 5: Side-by-side comparison with multimodal AI.GENERATE
-- ============================================================================
-- Compare deterministic layout chunking (`AI.CHUNK_DOCUMENT`) with single-pass
-- structured extraction (`AI.GENERATE` + `output_schema`) on the same PDF.

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
          'gs://your-gcp-project-id/bq_ai_functions/ai_chunk_document/docs/invoice_001.pdf',
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

-- DROP EXTERNAL TABLE IF EXISTS `your-gcp-project-id.bq_ai_functions.ai_chunk_document_docs`;
