-- =============================================================================
-- AI.TRANSLATE — SQL Companion
-- Replace `your-gcp-project-id` with your GCP project ID before running.
-- Dataset location: `US` (or `EU`) multi-region for regional data residency;
-- single regions (e.g. `us-central1`) route to the Cloud Translation global endpoint.
--
-- Prerequisites for AI.TRANSLATE (Examples 1–6):
--   * Cloud Translation API (`translate.googleapis.com`) enabled
--   * `roles/cloudtranslate.user` on the caller (end-user credentials; NO connection_id)
-- Additional prerequisites ONLY for Example 7's ML.TRANSLATE comparison:
--   * Cloud Resource connection `us.bq_ai_functions` with `roles/cloudtranslate.user`
-- =============================================================================


-- -----------------------------------------------------------------------------
-- Setup: shared dataset + sample multilingual customer feedback table
-- -----------------------------------------------------------------------------
CREATE SCHEMA IF NOT EXISTS `your-gcp-project-id.bq_ai_functions`
  OPTIONS (location = 'US');

CREATE OR REPLACE TABLE `your-gcp-project-id.bq_ai_functions.ai_translate_feedback` AS
SELECT * FROM UNNEST([
  STRUCT(
    1 AS id, 'es' AS declared_lang, 'es' AS preferred_reply_lang, 'billing' AS category,
    'El cargo apareció dos veces en mi factura de marzo y necesito un reembolso.' AS comment
  ),
  STRUCT(
    2, 'fr', 'fr', 'ux_idiom',
    "Franchement, votre nouvelle interface met dans le mille — bravo à toute l'équipe !"
  ),
  STRUCT(
    3, 'ja', 'ja', 'tech_jargon',
    'クエリ結果は速いですが、スロット予約の上限に達するとバッチジョブが待機状態になります。'
  ),
  STRUCT(
    4, 'de', 'de', 'ux_idiom',
    'Das Dashboard läuft wie am Schnürchen, aber beim CSV-Export klemmt es manchmal.'
  ),
  STRUCT(
    5, 'pt', 'pt', 'feature',
    'Seria ótimo poder exportar os relatórios semanais diretamente para uma planilha.'
  ),
  STRUCT(
    6, 'fr', 'fr', 'ambiguous_short',
    'chat'
  ),
  STRUCT(
    7, 'en', 'es', 'outbound_reply',
    'Your refund has been approved and will post to your card within three business days.'
  ),
  STRUCT(
    8, 'es', 'de', 'billing_idiom',
    'Me cobraron un ojo de la cara por el soporte prioritario y nadie respondió.'
  ),
  STRUCT(
    9, 'en', 'en', 'empty_edge',
    ''
  ),
  STRUCT(
    10, 'en', 'en', 'null_edge',
    CAST(NULL AS STRING)
  )
]);


-- -----------------------------------------------------------------------------
-- Example 1: Simplest starter call — inline scalar translation (zero DDL)
-- -----------------------------------------------------------------------------
SELECT
  id,
  declared_lang,
  comment,
  AI.TRANSLATE(comment, 'en') AS comment_en
FROM `your-gcp-project-id.bq_ai_functions.ai_translate_feedback`
WHERE id IN (1, 2, 3, 4, 5)
ORDER BY id;


-- -----------------------------------------------------------------------------
-- Example 2a: Dynamic per-row `target_language` column expression
-- Route one canonical English resolution into each customer's preferred locale.
-- -----------------------------------------------------------------------------
WITH outbound AS (
  SELECT
    id,
    preferred_reply_lang,
    'We resolved the duplicate charge and credited your account.' AS resolution_en
  FROM `your-gcp-project-id.bq_ai_functions.ai_translate_feedback`
  WHERE id IN (1, 2, 3, 4, 5)
)
SELECT
  id,
  preferred_reply_lang,
  AI.TRANSLATE(
    resolution_en,
    target_language => preferred_reply_lang,
    source_language => 'en'
  ) AS localized_reply
FROM outbound
ORDER BY id;


-- -----------------------------------------------------------------------------
-- Example 2b: Explicit `source_language` disambiguation on homographs
-- ('chat' = cat in FR vs online chat in EN; 'gift' = poison in DE vs present in EN)
-- -----------------------------------------------------------------------------
WITH homographs AS (
  SELECT * FROM UNNEST([
    STRUCT('chat' AS token, 'fr' AS declared_source, 'French noun ("cat")' AS context),
    STRUCT('chat',          'en',                    'English noun ("online chat")'),
    STRUCT('gift',          'de',                    'German noun ("poison")'),
    STRUCT('gift',          'en',                    'English noun ("present")')
  ])
)
SELECT
  token,
  declared_source,
  context,
  AI.TRANSLATE(token, 'es') AS auto_detect_to_es,
  AI.TRANSLATE(token, 'es', source_language => declared_source) AS explicit_source_to_es
FROM homographs;


-- -----------------------------------------------------------------------------
-- Example 3: Choosing the engine — `model => 'nmt'` vs `model => 'translation-llm'`
--   * 'nmt' (default): 500K input chars/mo free, then $20/1M input chars (output unbilled)
--   * 'translation-llm': $10/1M input chars + $10/1M output chars
-- -----------------------------------------------------------------------------
SELECT
  id,
  declared_lang,
  category,
  comment,
  AI.TRANSLATE(comment, 'en', model => 'nmt') AS nmt_en,
  AI.TRANSLATE(comment, 'en', model => 'translation-llm') AS translation_llm_en
FROM `your-gcp-project-id.bq_ai_functions.ai_translate_feedback`
WHERE id IN (2, 3, 4, 8)
ORDER BY id;


-- -----------------------------------------------------------------------------
-- Example 4: `return_details => TRUE` (`STRUCT<result STRING, status STRING, details JSON>`)
-- CRITICAL: AI.TRANSLATE sets `status = 'OK'` on success (NOT `status = ''`!).
-- `$.detected_language_code` is populated only when `source_language` is omitted.
-- -----------------------------------------------------------------------------
WITH detailed AS (
  SELECT
    id,
    declared_lang,
    AI.TRANSLATE(comment, 'en', return_details => TRUE) AS auto_src,
    AI.TRANSLATE(
      comment,
      'en',
      source_language => declared_lang,
      model => 'translation-llm',
      return_details => TRUE
    ) AS explicit_src
  FROM `your-gcp-project-id.bq_ai_functions.ai_translate_feedback`
  WHERE id IN (1, 2, 3)
)
SELECT
  id,
  auto_src.result AS nmt_result,
  auto_src.status AS nmt_status,
  JSON_VALUE(auto_src.details, '$.detected_language_code') AS auto_detected_lang,
  JSON_VALUE(auto_src.details, '$.model') AS nmt_backend_model,
  JSON_VALUE(explicit_src.details, '$.detected_language_code') AS explicit_detected_lang,
  JSON_VALUE(explicit_src.details, '$.model') AS tllm_backend_model
FROM detailed
WHERE auto_src.status = 'OK'
ORDER BY id;


-- -----------------------------------------------------------------------------
-- Example 5: Row-level boundary probes & compile-time signature guardrails
--   * NULL input -> entire STRUCT is NULL (`detailed IS NULL` is TRUE)
--   * '' empty string -> local short-circuit (`result = ''`, `status = 'OK'`, `details = {}`)
--   * Invalid per-row `target_language` -> silent NULL when `return_details => FALSE`,
--     vs `status = 'Target language is invalid.'` when `return_details => TRUE`
--
-- Compile-time guardrails (intentionally commented out — each raises HTTP 400):
--   -- 1) EUC-only (`connection_id` does not exist in signature):
--   -- SELECT AI.TRANSLATE('Hola', 'en', connection_id => 'us.bq_ai_functions');
--   -- 2) `model` must be an analysis-time constant, not a column expression:
--   -- SELECT AI.TRANSLATE(comment, 'en', model => declared_lang)
--   -- FROM `your-gcp-project-id.bq_ai_functions.ai_translate_feedback`;
--   -- 3) `model` must be 'nmt' or 'translation-llm':
--   -- SELECT AI.TRANSLATE('Hola', 'en', model => 'INVALID_MODEL_NAME');
-- -----------------------------------------------------------------------------
WITH edge_inputs AS (
  SELECT * FROM UNNEST([
    STRUCT(1 AS probe_id, 'NULL content' AS case_label, CAST(NULL AS STRING) AS txt, 'en' AS target_lang),
    STRUCT(2,             'Empty string (local short-circuit)', '',                   'en'),
    STRUCT(3,             'Whitespace-only string (calls backend)', '   ',            'en'),
    STRUCT(4,             'Invalid per-row target_language', 'Hola mundo',            'xx-invalid')
  ])
),
evaluated AS (
  SELECT
    probe_id,
    case_label,
    AI.TRANSLATE(txt, target_lang) AS plain_result,
    AI.TRANSLATE(txt, target_lang, return_details => TRUE) AS detailed
  FROM edge_inputs
)
SELECT
  probe_id,
  case_label,
  plain_result,
  detailed IS NULL AS struct_is_null,
  detailed.result AS detail_result,
  detailed.status AS detail_status,
  TO_JSON_STRING(detailed.details) AS detail_json
FROM evaluated
ORDER BY probe_id;


-- -----------------------------------------------------------------------------
-- Example 7: Four-way comparison — AI.TRANSLATE ('nmt' & 'translation-llm')
-- vs ML.TRANSLATE (`CLOUD_AI_TRANSLATE_V3`) vs AI.GENERATE (`gemini-3.5-flash-lite`)
-- -----------------------------------------------------------------------------
CREATE OR REPLACE MODEL `your-gcp-project-id.bq_ai_functions.ai_translate_ml_model`
  REMOTE WITH CONNECTION `your-gcp-project-id.us.bq_ai_functions`
  OPTIONS (REMOTE_SERVICE_TYPE = 'CLOUD_AI_TRANSLATE_V3');

WITH target_rows AS (
  SELECT id, declared_lang, comment
  FROM `your-gcp-project-id.bq_ai_functions.ai_translate_feedback`
  WHERE id IN (1, 2, 3, 4, 8)
),
ml_tvf AS (
  SELECT
    id,
    STRING(ml_translate_result.translations[0].translatedText) AS ml_translate_en
  FROM ML.TRANSLATE(
    MODEL `your-gcp-project-id.bq_ai_functions.ai_translate_ml_model`,
    (SELECT id, comment AS text_content FROM target_rows),
    STRUCT('TRANSLATE_TEXT' AS translate_mode, 'en' AS target_language_code)
  )
)
SELECT
  r.id,
  r.declared_lang,
  r.comment,
  AI.TRANSLATE(r.comment, 'en', model => 'nmt') AS ai_translate_nmt,
  m.ml_translate_en,
  AI.TRANSLATE(r.comment, 'en', model => 'translation-llm') AS ai_translate_tllm,
  AI.GENERATE(
    ('Translate the following text into natural English. Return only the translation, without quotes or commentary: ', r.comment),
    endpoint => 'gemini-3.5-flash-lite'
  ).result AS ai_generate_gemini
FROM target_rows AS r
JOIN ml_tvf AS m USING (id)
ORDER BY r.id;


-- -----------------------------------------------------------------------------
-- Cleanup: drop notebook-owned sample table and temporary comparison model
-- -----------------------------------------------------------------------------
DROP TABLE IF EXISTS `your-gcp-project-id.bq_ai_functions.ai_translate_feedback`;
DROP MODEL IF EXISTS `your-gcp-project-id.bq_ai_functions.ai_translate_ml_model`;
