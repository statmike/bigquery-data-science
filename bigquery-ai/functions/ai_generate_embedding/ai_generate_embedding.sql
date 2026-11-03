-- AI.GENERATE_EMBEDDING — Progressive SQL Examples
-- ==================================================
-- Table-valued function that creates embeddings via a remote model.
-- Requires CREATE MODEL. Input must have a 'content' column.
--
-- Returns: input columns + embedding ARRAY<FLOAT64>, status STRING
--   (plus statistics JSON on legacy text models gemini-embedding-001 / text-embedding-005;
--    gemini-embedding-2 omits statistics and rejects task_type/title)
--
-- Prerequisite: MODEL `PROJECT_ID.DATASET.embedding_text` pointing to gemini-embedding-2
-- Full reference: ../../RESOURCES.md
-- Official docs: https://cloud.google.com/bigquery/docs/reference/standard-sql/bigqueryml-syntax-ai-generate-embedding


-- =============================================================================
-- Example 1: Basic text embedding (gemini-embedding-2, 3072 dims default)
-- =============================================================================
SELECT content, ARRAY_LENGTH(embedding) AS dims, status
FROM AI.GENERATE_EMBEDDING(
  MODEL `PROJECT_ID.DATASET.embedding_text`,
  (SELECT text AS content
   FROM UNNEST(['BigQuery is a data warehouse.', 'Cloud computing scales.']) AS text)
);


-- =============================================================================
-- Example 2: Using task_type, title, and statistics (legacy text models only)
-- (gemini-embedding-2 is unified task-agnostic and omits statistics; use a model
--  pointing to gemini-embedding-001 or text-embedding-005 when task_type is needed)
-- =============================================================================
SELECT content, ARRAY_LENGTH(embedding) AS dims, statistics
FROM AI.GENERATE_EMBEDDING(
  MODEL `PROJECT_ID.DATASET.embedding_gemini`,
  (SELECT text AS content, 'Google Cloud Service Overview' AS title
   FROM UNNEST(['BigQuery', 'Cloud Functions', 'Cloud Storage']) AS text),
  STRUCT('RETRIEVAL_DOCUMENT' AS task_type)
);


-- =============================================================================
-- Example 3: Reducing dimensions with output_dimensionality for VECTOR_SEARCH
-- (Use STRUCT(768 AS output_dimensionality) on gemini-embedding-2 to stay under
--  BigQuery's <= 2,000-dimension limit for CREATE VECTOR INDEX)
-- =============================================================================
CREATE OR REPLACE TABLE `PROJECT_ID.DATASET.ai_generate_embedding_docs` AS
SELECT content, embedding
FROM AI.GENERATE_EMBEDDING(
  MODEL `PROJECT_ID.DATASET.embedding_text`,
  (SELECT text AS content
   FROM UNNEST([
     'BigQuery is a serverless data warehouse.',
     'Cloud Functions runs event-driven code.',
     'Cloud Storage stores objects.',
     'Kubernetes Engine runs containers.',
     'Pub/Sub is a messaging service.'
   ]) AS text),
  STRUCT(768 AS output_dimensionality)
);


-- =============================================================================
-- Example 4: Comparing models (gemini-embedding-2, gemini-embedding-001, text-embedding-005)
-- =============================================================================
SELECT
  'gemini-embedding-2' AS model,
  ARRAY_LENGTH(embedding) AS dims,
  status
FROM AI.GENERATE_EMBEDDING(
  MODEL `PROJECT_ID.DATASET.embedding_text`,
  (SELECT 'BigQuery is a data warehouse.' AS content)
)
UNION ALL
SELECT
  'gemini-embedding-001',
  ARRAY_LENGTH(embedding),
  status
FROM AI.GENERATE_EMBEDDING(
  MODEL `PROJECT_ID.DATASET.embedding_gemini`,
  (SELECT 'BigQuery is a data warehouse.' AS content)
)
UNION ALL
SELECT
  'text-embedding-005',
  ARRAY_LENGTH(embedding),
  status
FROM AI.GENERATE_EMBEDDING(
  MODEL `PROJECT_ID.DATASET.embedding_text_005`,
  (SELECT 'BigQuery is a data warehouse.' AS content)
);


-- =============================================================================
-- Example 5: Multimodal embedding model (gemini-embedding-2)
-- =============================================================================
CREATE OR REPLACE MODEL `PROJECT_ID.DATASET.embedding_multimodal`
  REMOTE WITH CONNECTION `PROJECT_ID.LOCATION.CONNECTION_ID`
  OPTIONS (endpoint = 'gemini-embedding-2');

-- Batch embed documents via inline ObjectRef (3072 dims default)
SELECT
  doc_name,
  ARRAY_LENGTH(embedding) AS dims
FROM AI.GENERATE_EMBEDDING(
  MODEL `PROJECT_ID.DATASET.embedding_multimodal`,
  (SELECT
    doc_name,
    OBJ.MAKE_REF(CONCAT('gs://BUCKET/path/to/', doc_name), 'PROJECT_ID.LOCATION.CONNECTION_ID') AS content
  FROM UNNEST([
    'invoice_1.png', 'invoice_2.png', 'receipt_1.png'
  ]) AS doc_name)
);


-- =============================================================================
-- Example 6: Custom embedding dimensions on multimodal inputs
-- =============================================================================
SELECT
  doc_name,
  ARRAY_LENGTH(embedding) AS dims
FROM AI.GENERATE_EMBEDDING(
  MODEL `PROJECT_ID.DATASET.embedding_multimodal`,
  (SELECT
    doc_name,
    OBJ.MAKE_REF(CONCAT('gs://BUCKET/path/to/', doc_name), 'PROJECT_ID.LOCATION.CONNECTION_ID') AS content
  FROM UNNEST(['invoice_1.png', 'invoice_2.png', 'invoice_3.png']) AS doc_name),
  STRUCT(768 AS output_dimensionality)
);
