-- AI.GENERATE — Progressive SQL Examples
-- =========================================
-- Scalar function that sends prompts to Gemini models and returns generated text
-- or structured output. No model creation required.
--
-- Default model: gemini-3.5-flash-lite (pin gemini-3.8-flash, gemini-4-argon,
--                gemini-4-carbon, or gemini-4-hydrogen)
-- Returns: STRUCT<result STRING, full_response JSON, status STRING>
--          (or custom schema fields when output_schema is specified)
-- Multimodal: Supports documents, images, and video via ObjectRef (see examples 13-15)
--
-- Full reference: ../../RESOURCES.md
-- Official docs: https://cloud.google.com/bigquery/docs/reference/standard-sql/bigqueryml-syntax-ai-generate


-- =============================================================================
-- Example 1: Simplest possible call — just a prompt string
-- =============================================================================
-- AI.GENERATE takes a prompt and returns a STRUCT.
-- Access the generated text with .result
SELECT
  (AI.GENERATE('What is BigQuery?')).result AS answer;


-- =============================================================================
-- Example 2: Using a column as input
-- =============================================================================
-- Use CONCAT to build prompts from column values.
-- AI.GENERATE runs once per row.
SELECT
  city,
  (AI.GENERATE(
    CONCAT('What country is ', city, ' in? Answer in one word.')
  )).result AS country
FROM UNNEST(['Tokyo', 'Paris', 'Nairobi', 'Lima', 'Sydney']) AS city;


-- =============================================================================
-- Example 3: Accessing the full response
-- =============================================================================
-- The function returns a STRUCT with three fields:
--   .result         — the generated text (STRING)
--   .full_response  — the complete API response (JSON)
--   .status         — error message if failed, empty if successful (STRING)
SELECT
  response.result,
  response.status,
  JSON_VALUE(response.full_response, '$.candidates[0].finishReason') AS finish_reason,
  JSON_VALUE(response.full_response, '$.usageMetadata.totalTokenCount') AS total_tokens
FROM (
  SELECT AI.GENERATE('Explain cloud computing in one sentence.') AS response
);


-- =============================================================================
-- Example 4: Specifying an endpoint
-- =============================================================================
-- Override the default model (gemini-3.5-flash-lite) with any GA Gemini 3.x or
-- Gemini 4 model:
--   - 'gemini-3.8-flash'    — Preferred Flash default ($0.75 / $3.75 per 1M
--                             input/output tokens through Dec 31, 2026; supports
--                             custom temperature)
--   - 'gemini-4-argon'      — Preferred Pro / frontier reasoning default
--                             ($2.00 / $10.00 through Nov 30, 2026; $4.00 / $20.00 Dec 1+)
--   - 'gemini-4-carbon'     — Frontier / Pro reasoning model (GA 2026-11-10;
--                             $2.00 / $10.00 through Nov 30, 2026; $4.00 / $20.00 Dec 1+)
--   - 'gemini-4-hydrogen'   — Gemini 4 speed & efficiency model for coding,
--                             agentic workflows, multimodal analysis, and tool use
--                             (GA 2026-11-12; $1.50 / $7.50 per 1M tokens)
SELECT
  endpoint,
  JSON_VALUE(resp.full_response, '$.model_version') AS model_version,
  resp.result AS haiku
FROM UNNEST([
  STRUCT(
    'gemini-3.8-flash' AS endpoint,
    AI.GENERATE('Write a haiku about data warehouses.', endpoint => 'gemini-3.8-flash') AS resp
  ),
  STRUCT(
    'gemini-4-argon',
    AI.GENERATE('Write a haiku about data warehouses.', endpoint => 'gemini-4-argon')
  ),
  STRUCT(
    'gemini-4-carbon',
    AI.GENERATE('Write a haiku about data warehouses.', endpoint => 'gemini-4-carbon')
  ),
  STRUCT(
    'gemini-4-hydrogen',
    AI.GENERATE('Write a haiku about data warehouses.', endpoint => 'gemini-4-hydrogen')
  )
]);


-- =============================================================================
-- Example 5: Structured output with output_schema
-- =============================================================================
-- When you provide an output_schema, the result field is replaced by
-- typed columns matching your schema.
SELECT
  animal,
  result.*
FROM
  UNNEST(['Eagle', 'Salmon', 'Cobra']) AS animal,
  UNNEST([
    AI.GENERATE(
      CONCAT('Give me facts about: ', animal),
      output_schema => 'habitat STRING, average_lifespan_years INT64, is_endangered BOOL'
    )
  ]) AS result;


-- =============================================================================
-- Example 6: Structured output with field descriptions
-- =============================================================================
-- Add OPTIONS(description = '...') to guide the model on what each field means.
SELECT
  product,
  result.*
FROM
  UNNEST(['laptop', 'running shoes', 'espresso machine']) AS product,
  UNNEST([
    AI.GENERATE(
      CONCAT('Analyze this product for an e-commerce listing: ', product),
      output_schema => """
        category STRING OPTIONS(description = 'Product category like Electronics, Apparel, Kitchen'),
        price_range_usd STRING OPTIONS(description = 'Estimated price range like $50-$100'),
        key_features ARRAY<STRING> OPTIONS(description = 'Top 3 selling points'),
        needs_batteries BOOL OPTIONS(description = 'Whether the product typically requires batteries')
      """
    )
  ]) AS result;


-- =============================================================================
-- Example 7: Using model_params — temperature
-- =============================================================================
-- model_params accepts any field from the Gemini generateContent request body
-- (except 'contents'). Use generation_config to control temperature, top_p, etc.
-- Note: Gemini 4 models ('gemini-4-argon', 'gemini-4-carbon', 'gemini-4-hydrogen')
-- ignore custom sampling parameters (temperature, top_p, top_k). Pin
-- 'gemini-3.8-flash' when custom temperature control is required.
SELECT
  (AI.GENERATE(
    'Invent a creative name for a new coffee shop.',
    endpoint => 'gemini-3.8-flash',
    model_params => JSON '{"generation_config": {"temperature": 1.5}}'
  )).result AS creative_name;


-- =============================================================================
-- Example 8: Using model_params — thinking_level
-- =============================================================================
-- Gemini 3.x ('gemini-3.8-flash') and Gemini 4 ('gemini-4-argon',
-- 'gemini-4-carbon', 'gemini-4-hydrogen') models configure reasoning depth via
-- thinking_level ("LOW", "MEDIUM", "HIGH") in thinking_config.
--
-- Empirical BigQuery SQL validation notes for Gemini 4:
--   - All three Gemini 4 models share a unified 1,048,576-token input+output
--     window, ignore custom sampling parameters (temperature, top_p, top_k),
--     and use thinking_config.thinking_level instead of thinking_budget.
--   - In BigQuery SQL model_params, thinking_level accepts "LOW", "MEDIUM"
--     (default), and "HIGH" on all three Gemini 4 models. Even though the
--     Vertex AI Gemini 4 Hydrogen model card lists "XHIGH", BigQuery's SQL
--     model_params GenerateContent proto validator rejects both "MINIMAL" and
--     "XHIGH" (as well as thinking_budget) at query analysis time with:
--     400 The model_params is invalid and does not conform to the GenerateContent request body.
SELECT
  endpoint,
  thinking_level,
  INT64(JSON_QUERY(resp.full_response, '$.usage_metadata.thoughts_token_count')) AS thoughts_tokens,
  resp.result AS answer
FROM UNNEST([
  STRUCT(
    'gemini-4-argon' AS endpoint,
    'LOW' AS thinking_level,
    AI.GENERATE(
      'What is the sum of all prime numbers less than 50?',
      endpoint => 'gemini-4-argon',
      model_params => JSON '{"generation_config": {"thinking_config": {"thinking_level": "LOW"}}}'
    ) AS resp
  ),
  STRUCT(
    'gemini-4-carbon',
    'LOW',
    AI.GENERATE(
      'What is the sum of all prime numbers less than 50?',
      endpoint => 'gemini-4-carbon',
      model_params => JSON '{"generation_config": {"thinking_config": {"thinking_level": "LOW"}}}'
    )
  ),
  STRUCT(
    'gemini-4-hydrogen',
    'LOW',
    AI.GENERATE(
      'What is the sum of all prime numbers less than 50?',
      endpoint => 'gemini-4-hydrogen',
      model_params => JSON '{"generation_config": {"thinking_config": {"thinking_level": "LOW"}}}'
    )
  ),
  STRUCT(
    'gemini-4-hydrogen',
    'HIGH',
    AI.GENERATE(
      'What is the sum of all prime numbers less than 50?',
      endpoint => 'gemini-4-hydrogen',
      model_params => JSON '{"generation_config": {"thinking_config": {"thinking_level": "HIGH"}}}'
    )
  )
]);


-- =============================================================================
-- Example 9: Grounding with Google Search
-- =============================================================================
-- Use the tools field in model_params to enable Google Search grounding.
-- The model will search the web for current information before responding.
SELECT
  (AI.GENERATE(
    'What were the top 3 news stories today?',
    model_params => JSON '{"tools": [{"googleSearch": {}}]}'
  )).result AS grounded_answer;


-- =============================================================================
-- Example 10: Using a connection
-- =============================================================================
-- By default, AI.GENERATE uses end-user credentials. Specify a connection
-- to use a service account instead. This is useful for:
--   - Queries that may run longer than 48 hours
--   - Consistent permissions across users
--   - Service account-based access control
--
-- Replace 'PROJECT_ID.LOCATION.CONNECTION_ID' with your connection.

-- SELECT
--   (AI.GENERATE(
--     'What is BigQuery?',
--     connection_id => 'your-project.us.your-connection'
--   )).result AS answer;


-- =============================================================================
-- Example 11: Using request_type for Provisioned Throughput
-- =============================================================================
-- Control which quota pool is used:
--   'UNSPECIFIED' (default) — Provisioned Throughput first, overflow to DSQ
--   'DEDICATED'             — Provisioned Throughput only (errors if unavailable)
--   'SHARED'                — Dynamic Shared Quota only

-- SELECT
--   (AI.GENERATE(
--     'Summarize the benefits of serverless computing.',
--     request_type => 'SHARED'
--   )).result AS answer;


-- =============================================================================
-- Example 12: Processing table data at scale
-- =============================================================================
-- Best practice: when using LIMIT, materialize selected rows first to avoid
-- re-evaluating the subquery and incurring extra Vertex AI charges.
WITH selected_reviews AS (
  SELECT *
  FROM UNNEST([
    STRUCT('r1' AS id, 'The product is amazing, fast delivery!' AS review),
    STRUCT('r2', 'Terrible quality. Broke after one day.'),
    STRUCT('r3', 'Average product, nothing special.'),
    STRUCT('r4', 'Great value for the price. Highly recommend!'),
    STRUCT('r5', 'Worst purchase ever. Do not buy.')
  ])
)
SELECT
  id,
  review,
  (AI.GENERATE(
    CONCAT('Classify this review sentiment as positive, negative, or neutral: ', review),
    output_schema => 'sentiment STRING, confidence FLOAT64'
  )).*
FROM selected_reviews;


-- =============================================================================
-- Example 13: Describe a document with ObjectRef
-- =============================================================================
-- The ObjectRef pipeline turns a GCS URI into a signed reference that
-- AI.GENERATE can read. Pass it in a STRUCT with prompt and
-- object_refs fields.
--
-- Requires: Cloud resource connection with roles/storage.objectViewer
SELECT
  (AI.GENERATE(
    STRUCT(
      'Describe what this document is and summarize its key details.' AS prompt,
      [OBJ.MAKE_REF('gs://BUCKET/path/to/document.pdf', 'PROJECT_ID.LOCATION.CONNECTION_ID')] AS object_refs
    )
  )).result AS description;


-- =============================================================================
-- Example 14: Extract structured data from a document
-- =============================================================================
-- Combine ObjectRef with output_schema to extract typed fields from
-- documents — no Document AI processor needed.
SELECT
  result.vendor_name,
  result.invoice_number,
  result.total_amount,
  result.currency,
  result.invoice_date,
  result.line_item_count
FROM UNNEST([
  AI.GENERATE(
    STRUCT(
      'Extract the key fields from this invoice.' AS prompt,
      [OBJ.MAKE_REF('gs://BUCKET/path/to/invoice.pdf', 'PROJECT_ID.LOCATION.CONNECTION_ID')] AS object_refs
    ),
    output_schema => 'vendor_name STRING, invoice_number STRING, total_amount FLOAT64, currency STRING, invoice_date STRING, line_item_count INT64'
  )
]) AS result;


-- =============================================================================
-- Example 15: Process multiple documents
-- =============================================================================
-- Process different document types in a single query by building ObjectRef
-- from a list of URIs.
SELECT
  uri,
  result.document_type,
  result.total_amount,
  result.date,
  result.summary
FROM
  UNNEST([
    'gs://BUCKET/path/to/invoice.pdf',
    'gs://BUCKET/path/to/receipt.pdf'
  ]) AS uri,
  UNNEST([
    AI.GENERATE(
      STRUCT(
        'Identify the document type and extract key details.' AS prompt,
        [OBJ.MAKE_REF(uri, 'PROJECT_ID.LOCATION.CONNECTION_ID')] AS object_refs
      ),
      output_schema => 'document_type STRING, total_amount FLOAT64, date STRING, summary STRING'
    )
  ]) AS result;


-- =============================================================================
-- Example 16: Discover documents with OBJ.LIST (GA)
-- =============================================================================
-- One wildcard path returns every matching object's metadata plus a ready
-- ObjectRef in the ref column -- no hand-built URI list, no object table.
-- The connection argument is optional: omit it for direct access (read as the
-- query runner), pass it for delegated access through the connection.
SELECT
  uri,
  content_type,
  size,
  result.document_type,
  result.total_amount,
  result.summary
FROM
  OBJ.LIST('gs://BUCKET/path/to/*.pdf', 'PROJECT_ID.LOCATION.CONNECTION_ID'),
  UNNEST([
    AI.GENERATE(
      STRUCT(
        'Identify the document type and extract key details.' AS prompt,
        [ref] AS object_refs
      ),
      output_schema => 'document_type STRING, total_amount FLOAT64, summary STRING'
    )
  ]) AS result
ORDER BY uri;
