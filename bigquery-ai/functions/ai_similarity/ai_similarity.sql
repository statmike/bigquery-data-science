-- AI.SIMILARITY — Progressive SQL Examples
-- ==========================================
-- Scalar function that computes cosine similarity between two inputs.
-- Generates embeddings at runtime. No pre-computed embeddings needed.
--
-- Returns: FLOAT64 (cosine similarity, closer to 1 = more similar)
--
-- Full reference: ../../RESOURCES.md
-- Official docs: https://cloud.google.com/bigquery/docs/reference/standard-sql/bigqueryml-syntax-ai-similarity


-- =============================================================================
-- Example 1: Basic text similarity (gemini-embedding-2)
-- =============================================================================
SELECT
  AI.SIMILARITY(
    content1 => 'BigQuery is a data warehouse',
    content2 => 'BigQuery stores and analyzes data',
    endpoint => 'gemini-embedding-2'
  ) AS similarity;


-- =============================================================================
-- Example 2: Comparing multiple pairs
-- =============================================================================
SELECT
  text_a,
  text_b,
  AI.SIMILARITY(
    content1 => text_a,
    content2 => text_b,
    endpoint => 'gemini-embedding-2'
  ) AS similarity
FROM
  UNNEST(['machine learning', 'deep learning', 'cooking recipes']) AS text_a,
  UNNEST(['artificial intelligence', 'neural networks', 'baking bread']) AS text_b
ORDER BY similarity DESC;


-- =============================================================================
-- Example 3: Finding the best match
-- =============================================================================
SELECT product,
  AI.SIMILARITY(
    content1 => 'comfortable typing device',
    content2 => product,
    endpoint => 'gemini-embedding-2'
  ) AS similarity
FROM UNNEST([
  'mechanical keyboard with ergonomic design',
  'wireless mouse with adjustable DPI',
  'standing desk with memory presets'
]) AS product
ORDER BY similarity DESC
LIMIT 1;


-- =============================================================================
-- Example 4: Semantic deduplication
-- =============================================================================
WITH items AS (
  SELECT *
  FROM UNNEST([
    STRUCT(1 AS id, 'BigQuery data warehouse' AS text),
    STRUCT(2, 'BigQuery serverless warehouse'),
    STRUCT(3, 'Cloud Functions serverless'),
    STRUCT(4, 'Cloud Functions event-driven compute')
  ])
)
SELECT
  a.id AS id_a, a.text AS text_a,
  b.id AS id_b, b.text AS text_b,
  AI.SIMILARITY(content1 => a.text, content2 => b.text, endpoint => 'gemini-embedding-2') AS similarity
FROM items a, items b
WHERE a.id < b.id
  AND AI.SIMILARITY(content1 => a.text, content2 => b.text, endpoint => 'gemini-embedding-2') > 0.75
ORDER BY similarity DESC;


-- =============================================================================
-- Example 5: Built-in model (no Vertex AI charges)
-- =============================================================================
SELECT
  text_a,
  text_b,
  AI.SIMILARITY(
    content1 => text_a,
    content2 => text_b,
    model => 'embeddinggemma-300m'
  ) AS similarity
FROM
  UNNEST(['machine learning', 'deep learning', 'cooking recipes']) AS text_a,
  UNNEST(['artificial intelligence', 'neural networks', 'baking bread']) AS text_b
ORDER BY similarity DESC;


-- =============================================================================
-- Example 6: Document-to-document similarity (multimodal with gemini-embedding-2)
-- =============================================================================
-- Requires: connection with aiplatform.user + storage.objectViewer roles
-- Uses inline ObjectRef pipeline with gemini-embedding-2
-- Same-type documents should score higher than cross-type pairs
SELECT
  AI.SIMILARITY(
    content1 => OBJ.MAKE_REF('gs://BUCKET/path/to/invoice_1.png', 'PROJECT_ID.LOCATION.CONNECTION_ID'),
    content2 => OBJ.MAKE_REF('gs://BUCKET/path/to/receipt_1.png', 'PROJECT_ID.LOCATION.CONNECTION_ID'),
    endpoint => 'gemini-embedding-2',
    connection_id => 'PROJECT_ID.LOCATION.CONNECTION_ID'
  ) AS similarity;


-- =============================================================================
-- Example 7: Cross-modal similarity (text to document)
-- =============================================================================
-- Compare text descriptions against document images — multimodal embeddings share a vector space
SELECT
  description,
  doc_name,
  ROUND(AI.SIMILARITY(
    content1 => description,
    content2 => OBJ.MAKE_REF(CONCAT('gs://BUCKET/path/to/', doc_name), 'PROJECT_ID.LOCATION.CONNECTION_ID'),
    endpoint => 'gemini-embedding-2',
    connection_id => 'PROJECT_ID.LOCATION.CONNECTION_ID'
  ), 4) AS similarity
FROM
  UNNEST(['a business invoice', 'a store receipt']) AS description,
  UNNEST(['invoice_1.png', 'receipt_1.png']) AS doc_name
ORDER BY description, similarity DESC;
