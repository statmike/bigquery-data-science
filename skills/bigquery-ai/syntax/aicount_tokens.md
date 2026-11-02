# `AI.COUNT_TOKENS`

> **Source:** [`bigquery-ai/reference/general-purpose-functions.md#aicount_tokens`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ai/reference/general-purpose-functions.md#aicount_tokens)

- **Description:** Utility scalar function that estimates the **input** token count of a text prompt. Token counting happens inside BigQuery and **incurs no Vertex AI charges** — unlike the generative functions, it does not send a generation request. Use it to estimate the cost or size of prompts before calling the paid AI functions.
- **Use cases:** Estimating the cost of an `AI.GENERATE` / `AI.GENERATE_TABLE` job before running it, checking prompts against a model's input token limit, comparing prompt sizes across rows/templates/models.
- [documentation](https://docs.cloud.google.com/bigquery/docs/reference/standard-sql/bigqueryml-syntax-ai-count-tokens)
- **Type:** Scalar function (returns a STRUCT value per row) — GA

**Syntax:**
```sql
AI.COUNT_TOKENS(
  INPUT
  [, endpoint => ENDPOINT]
)
```

**Inputs:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `INPUT` | STRING | Required | -- | The input text prompt for which to count tokens. |
| `endpoint` | STRING literal (named parameter) | Optional | The default model used by `AI.GENERATE` | Name of the generative AI model whose tokenization rules to use (e.g. `'gemini-2.5-pro'`). |

**Outputs:** Returns a `STRUCT` with:

| Field | Type | Description |
|-------|------|-------------|
| `result` | INT64 | Total **input** token count. `NULL` if the input is `NULL` or an API error occurred. |
| `full_response` | JSON | Per-modality token detail, e.g. `{"promptTokensDetails":[{"modality":"TEXT","tokenCount":180}],"totalTokens":180}`. `NULL` on `NULL` input or API error. |

**Best practices:**
- Because counting is free, aggregate `AI.COUNT_TOKENS(col).result` across a column (`SUM`/`AVG`/`MAX`) to size a batch workload before running the paid generation functions over it.
- Match the `endpoint` to the model you plan to generate with, so the token estimate reflects that model's tokenizer.

**Limitations:**
- Counts **input** tokens only — **thinking and output tokens are not included**. To see actual token counts (input + thinking + output) for a query, view the **Job information** tab of the Query results pane.
- **Text input only (re-verified at GA on 2026-11-02).** At GA, the `INPUT` argument still coerces strictly to `STRING` only — multimodal/`ObjectRef` prompts remain unsupported: a `STRUCT` prompt (`STRUCT(text AS prompt, [...] AS object_refs)`), the `ObjectRefRuntime` spelling, and a bare `ObjectRef` all fail coercion with:
  ```
  No matching signature for function BIGQUERYGOOGLESQL:AI.COUNT_TOKENS
    Argument types: STRUCT<uri STRING, version STRING, authorizer STRING, ...>
    Signature: AI.COUNT_TOKENS(STRING, [endpoint => STRING], [title => STRING], [model => STRING])
      Argument 1: Unable to coerce type STRUCT<...> to expected type STRING
  ```
  Accordingly, `full_response.promptTokensDetails[].modality` is always `TEXT`.

**Undocumented parameters (re-verified at GA on 2026-11-02):** the engine's printed signature remains `AI.COUNT_TOKENS(STRING, [endpoint => STRING], [title => STRING], [model => STRING])`, with only `endpoint` documented and general-purpose. `model` is mutually exclusive with `endpoint`, and `title` is rejected on Gemini generation endpoints; keep queries restricted to `(INPUT [, endpoint => ENDPOINT])`.

**Locations:** All BigQuery regions supporting the generative AI functions (US and EU multi-regions, plus supported Gemini regions).

**Provisioned throughput:** Not applicable — no Vertex AI request is made.

**BigFrames API:** No native wrapper. Use `%%bigquery` magics or `session.read_gbq_query()` to run `AI.COUNT_TOKENS` SQL from BigFrames.
