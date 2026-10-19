# `ML.GENERATE_TEXT`

> **Source:** [`bigquery-ai/reference/general-purpose-functions.md#mlgenerate_text`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ai/reference/general-purpose-functions.md#mlgenerate_text)

- **Description:** Table-valued function that performs generative natural language tasks. Functionally identical to `AI.GENERATE_TEXT` but with `ml_generate_text_*` prefixed column names and an additional `flatten_json_output` parameter. **Google recommends using `AI.GENERATE_TEXT` instead for new queries.**
- **Use cases:** Same as AI.GENERATE_TEXT: classification, sentiment analysis, image captioning, transcription, text enrichment, audio analysis, PDF analysis, etc.
- [documentation](https://docs.cloud.google.com/bigquery/docs/reference/standard-sql/bigqueryml-syntax-generate-text)
- **Type:** Table-valued function (returns a table with input columns plus output columns)

**Syntax (Gemini, standard tables):**
```sql
ML.GENERATE_TEXT(
  MODEL `PROJECT_ID.DATASET.MODEL`,
  { TABLE `PROJECT_ID.DATASET.TABLE` | (QUERY_STATEMENT) },
  STRUCT(
    { { [MAX_OUTPUT_TOKENS AS max_output_tokens]
        [, TOP_P AS top_p]
        [, TEMPERATURE AS temperature]
        [, STOP_SEQUENCES AS stop_sequences]
        [, GROUND_WITH_GOOGLE_SEARCH AS ground_with_google_search]
        [, SAFETY_SETTINGS AS safety_settings]
      }
      | [, MODEL_PARAMS AS model_params]
    }
    [, FLATTEN_JSON_OUTPUT AS flatten_json_output]
    [, REQUEST_TYPE AS request_type]
  )
)
```

Other model type syntaxes (Claude, Llama, Mistral AI, Open models, Object tables) follow the same pattern as AI.GENERATE_TEXT but with the added `flatten_json_output` parameter.

**Key difference from AI.GENERATE_TEXT -- The `flatten_json_output` parameter:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `flatten_json_output` | BOOL | FALSE | When TRUE, JSON response is parsed into separate columns (changes column names). |

All other parameters are identical to AI.GENERATE_TEXT.

**Outputs (key difference -- column naming):**

When `flatten_json_output` is FALSE (default):

| Column | Type | Description |
|--------|------|-------------|
| `ml_generate_text_result` | JSON | Full JSON response |
| `ml_generate_text_status` | STRING | API status (empty = success) |

When `flatten_json_output` is TRUE:

| Column | Type | Description |
|--------|------|-------------|
| `ml_generate_text_llm_result` | STRING | Generated text |
| `ml_generate_text_rai_result` | STRING | Safety ratings (Gemini only, when safety_settings specified) |
| `ml_generate_text_grounding_result` | STRING | Grounding sources (Gemini only, when ground_with_google_search is TRUE) |
| `ml_generate_text_status` | STRING | API status |

**Supported models:** Same as AI.GENERATE_TEXT (remote models over Gemini, Claude, Llama, Mistral, open models). Also explicitly supports remote models over fine-tuned Gemini models.

**Best practices / Limitations / Locations / Provisioned throughput:** Same as AI.GENERATE_TEXT.

**BigFrames API:** No direct `ML.GENERATE_TEXT` wrapper. BigFrames routes through `AI.GENERATE_TEXT` instead. Use `bbq.ai.generate_text()` or `GeminiTextGenerator`/`Claude3TextGenerator` classes (which generate `AI.GENERATE_TEXT` SQL under the hood).

---
