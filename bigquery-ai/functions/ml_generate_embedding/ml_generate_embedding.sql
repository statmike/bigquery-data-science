-- ML.GENERATE_EMBEDDING — Progressive SQL Examples
-- ==================================================
-- Legacy predecessor to AI.GENERATE_EMBEDDING.
-- Same capabilities but with ml_generate_embedding_ column prefixes.
-- Google recommends AI.GENERATE_EMBEDDING for new queries.
--
-- Prerequisite: a remote model pointing to gemini-embedding-2
-- Full reference: ../../RESOURCES.md
-- Official docs: https://cloud.google.com/bigquery/docs/reference/standard-sql/bigqueryml-syntax-generate-embedding


-- =============================================================================
-- Example 1: Basic text embedding
-- (Note: gemini-embedding-2 omits ml_generate_embedding_statistics)
-- =============================================================================
SELECT content,
  ARRAY_LENGTH(ml_generate_embedding_result) AS dims,
  ml_generate_embedding_status
FROM ML.GENERATE_EMBEDDING(
  MODEL `PROJECT_ID.DATASET.embedding_text`,
  (SELECT text AS content
   FROM UNNEST(['BigQuery is a data warehouse.', 'Cloud computing scales.']) AS text)
);


-- =============================================================================
-- Example 2: Reducing dimensions with output_dimensionality
-- (gemini-embedding-2 is task-agnostic and rejects task_type; use
--  output_dimensionality => 768 for <= 2,000-dim vector indexes)
-- =============================================================================
SELECT content,
  ARRAY_LENGTH(ml_generate_embedding_result) AS dims,
  ml_generate_embedding_status
FROM ML.GENERATE_EMBEDDING(
  MODEL `PROJECT_ID.DATASET.embedding_text`,
  (SELECT text AS content
   FROM UNNEST(['BigQuery', 'Cloud Functions', 'Cloud Storage']) AS text),
  STRUCT(768 AS output_dimensionality, TRUE AS flatten_json_output)
);
