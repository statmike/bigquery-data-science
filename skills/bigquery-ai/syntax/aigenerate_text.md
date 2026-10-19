# `AI.GENERATE_TEXT`

> **Source:** [`bigquery-ai/reference/general-purpose-functions.md#aigenerate_text`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ai/reference/general-purpose-functions.md#aigenerate_text)

- **Description:** Table-valued function that performs generative natural language tasks using any combination of text and unstructured data from BigQuery standard tables, or unstructured data from BigQuery object tables. Requires a pre-created remote model via `CREATE MODEL` that represents a Vertex AI model.
- **Use cases:** Classification, sentiment analysis, image captioning, transcription, text enrichment/summarization, audio content analysis, PDF content analysis, visual content analysis, entity extraction with structured JSON output, Google Search grounding, context caching.
- [documentation](https://docs.cloud.google.com/bigquery/docs/reference/standard-sql/bigqueryml-syntax-ai-generate-text)
- **Type:** Table-valued function (returns a table with input columns plus output columns)

**Syntax (Gemini, standard tables):**
```sql
AI.GENERATE_TEXT(
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
    [, REQUEST_TYPE AS request_type]
  )
)
```

**Syntax (Claude, standard tables):**
```sql
AI.GENERATE_TEXT(
  MODEL `PROJECT_ID.DATASET.MODEL`,
  { TABLE `PROJECT_ID.DATASET.TABLE` | (QUERY_STATEMENT) },
  STRUCT(
    { { [MAX_OUTPUT_TOKENS AS max_output_tokens]
        [, TOP_K AS top_k]
        [, TOP_P AS top_p]
      }
      | [, MODEL_PARAMS AS model_params]
    }
  )
)
```

**Syntax (Llama / Mistral AI, standard tables):**
```sql
AI.GENERATE_TEXT(
  MODEL `PROJECT_ID.DATASET.MODEL`,
  { TABLE `PROJECT_ID.DATASET.TABLE` | (QUERY_STATEMENT) },
  STRUCT(
    { { [MAX_OUTPUT_TOKENS AS max_output_tokens]
        [, TOP_P AS top_p]
        [, TEMPERATURE AS temperature]
        [, STOP_SEQUENCES AS stop_sequences]
      }
      | [, MODEL_PARAMS AS model_params]
    }
  )
)
```

**Syntax (Open models, standard tables):**
```sql
AI.GENERATE_TEXT(
  MODEL `PROJECT_ID.DATASET.MODEL`,
  { TABLE `PROJECT_ID.DATASET.TABLE` | (QUERY_STATEMENT) },
  STRUCT(
    { { [MAX_OUTPUT_TOKENS AS max_output_tokens]
        [, TOP_K AS top_k]
        [, TOP_P AS top_p]
        [, TEMPERATURE AS temperature]
        [, USE_CHAT_MODE AS use_chat_mode]
      }
      | [, MODEL_PARAMS AS model_params]
    }
  )
)
```

**Syntax (Object tables, Gemini only):**
```sql
AI.GENERATE_TEXT(
  MODEL `PROJECT_ID.DATASET.MODEL`,
  { TABLE `PROJECT_ID.DATASET.TABLE` | (QUERY_STATEMENT) },
  STRUCT(
    PROMPT AS prompt
    { { [, MAX_OUTPUT_TOKENS AS max_output_tokens]
        [, TOP_P AS top_p]
        [, TEMPERATURE AS temperature]
        [, STOP_SEQUENCES AS stop_sequences]
        [, SAFETY_SETTINGS AS safety_settings]
      }
      | [, MODEL_PARAMS AS model_params]
    }
  )
)
```

**Inputs (all model types combined):**

| Parameter | Type | Availability | Required | Default | Range | Description |
|-----------|------|-------------|----------|---------|-------|-------------|
| `MODEL` | Model reference | All | Required | -- | -- | Name of the remote model (`PROJECT_ID.DATASET.MODEL`) |
| `TABLE` / `QUERY_STATEMENT` | Table/Query | All | Required (one of) | -- | -- | Input data. Must have a `prompt` column. If no prompt column exists, use QUERY_STATEMENT with an alias. |
| `PROMPT` (object tables) | STRING | Gemini object tables | Required | -- | <16,000 tokens | Prompt for analyzing visual content |
| `max_output_tokens` | INT64 | All | Optional | 1024 | Gemini: [1,8192]; Claude/Llama/Mistral/Open: [1,4096] | Max tokens in response |
| `top_p` | FLOAT64 | All | Optional | 0.95 (Gemini, Llama, Mistral); model-determined (Claude, Open) | [0.0, 1.0] | Nucleus sampling parameter |
| `temperature` | FLOAT64 | Gemini, Llama, Mistral, Open | Optional | 0 (Gemini, Llama, Mistral); model-determined (Open) | [0.0, 1.0] | Randomness in token selection |
| `top_k` | INT64 | Claude, Open | Optional | Model-determined | [1, 40] | Top-K sampling |
| `stop_sequences` | ARRAY\<STRING\> | Gemini, Llama, Mistral | Optional | Empty array | -- | Strings to exclude from responses |
| `ground_with_google_search` | BOOL | Gemini | Optional | FALSE | -- | Enable Google Search grounding |
| `safety_settings` | ARRAY\<STRUCT\<STRING AS category, STRING AS threshold\>\> | Gemini | Optional | BLOCK_MEDIUM_AND_ABOVE | -- | Content safety filtering |
| `request_type` | STRING | Gemini | Optional | UNSPECIFIED | SHARED, DEDICATED, UNSPECIFIED | Quota type for Provisioned Throughput |
| `use_chat_mode` | BOOL | Open models | Optional | FALSE | -- | When TRUE, enables chat mode for open models. |
| `model_params` | JSON string | All | Optional | -- | -- | JSON conforming to generateContent request body. Cannot be used simultaneously with top-level parameters. |

Safety settings categories: `HARM_CATEGORY_HATE_SPEECH`, `HARM_CATEGORY_DANGEROUS_CONTENT`, `HARM_CATEGORY_HARASSMENT`, `HARM_CATEGORY_SEXUALLY_EXPLICIT`

Safety thresholds: `BLOCK_NONE` (Restricted), `BLOCK_LOW_AND_ABOVE`, `BLOCK_MEDIUM_AND_ABOVE` (Default), `BLOCK_ONLY_HIGH`, `HARM_BLOCK_THRESHOLD_UNSPECIFIED`

**Outputs (vary by model type):**

All models return the input table columns plus:

| Model Type | Column | Type | Description |
|------------|--------|------|-------------|
| Gemini | `result` | STRING | Generated text |
| Gemini | `rai_result` | JSON | Responsible AI result/safety attributes |
| Gemini | `grounding_result` | JSON | Grounding sources (when grounding enabled) |
| Gemini | `statistics` | JSON | Generation statistics (e.g., token counts) |
| Gemini | `full_response` | JSON | Complete Vertex AI API JSON response |
| Gemini | `status` | STRING | API status (empty = success) |
| Claude | `result` | STRING | Generated text |
| Claude | `full_response` | JSON | Complete Vertex AI API JSON response |
| Claude | `status` | STRING | API status |
| Llama | `result` | STRING | Generated text |
| Llama | `full_response` | JSON | Complete Vertex AI API JSON response |
| Llama | `status` | STRING | API status |
| Mistral AI | `result` | STRING | Generated text |
| Mistral AI | `full_response` | JSON | Complete Vertex AI API JSON response |
| Mistral AI | `status` | STRING | API status |
| Open models | `result` | STRING | Generated text |
| Open models | `full_response` | JSON | Complete Vertex AI API JSON response |
| Open models | `status` | STRING | API status |

**Supported models:** Remote models over any GA or preview Gemini models, Anthropic Claude models, Mistral AI models, Llama models, and supported open models (all via `CREATE MODEL`).

**Best practices:**
- Avoid using LIMIT and OFFSET in the prompt query (causes processing all data first). Write query results to a table first, then reference that table.
- Model and input table must be in the same region.

**Limitations:**
- Model and input table must be in the same region.
- Resource exhausted errors can occur for some rows when API call volume exceeds quota limits. Use BigQuery remote inference SQL scripts or Dataform package to handle quota errors iteratively.
- Gemini 2.5 models incur thinking process charges.
- Object table Cloud Storage bucket must be in the same project as the model.
- Object table queries only support WHERE and ORDER BY clauses.
- Object table prompt must be under 16,000 tokens.

**Locations:** Must run in the same region or multi-region as the remote model. Gemini: all supported Gemini regions plus US and EU multi-regions. Claude, Llama, Mistral AI: see Google Cloud partner model endpoint locations.

**Provisioned throughput:** Supported via `request_type` parameter; must pre-purchase matching quota.

**BigFrames API:** `bigframes.bigquery.ai.generate_text(model, data)` — TVF wrapper that takes a model name string and DataFrame/Series. Also available as `bigframes.ml.llm.GeminiTextGenerator` (sklearn-style: create model, then `.predict()`). GeminiTextGenerator also supports `.fit()` for fine-tuning and `.score()` for evaluation. For Claude models: `bigframes.ml.llm.Claude3TextGenerator`.

---
