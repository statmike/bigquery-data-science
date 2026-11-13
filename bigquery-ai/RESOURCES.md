![tracker](https://us-central1-vertex-ai-mlops-369716.cloudfunctions.net/pixel-tracking?path=statmike%2Fbigquery-data-science%2Fbigquery-ai&file=RESOURCES.md)
<!--- header table --->
<table>
<tr>     
  <td style="text-align: center">
    <a href="https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ai/RESOURCES.md">
      <img width="32px" src="https://raw.githubusercontent.com/statmike/bigquery-data-science/main/architectures/headers/icons/github.svg" alt="GitHub logo">
      <br>View on<br>GitHub
    </a>
  </td>
</tr>
<tr>
  <td style="text-align: right">
    <b>Share On: </b> 
    <a href="https://www.linkedin.com/sharing/share-offsite/?url=https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ai/RESOURCES.md"><img src="https://raw.githubusercontent.com/statmike/bigquery-data-science/main/architectures/headers/icons/linkedin.svg" alt="Linkedin Logo" width="20px"></a> 
    <a href="https://reddit.com/submit?url=https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ai/RESOURCES.md"><img src="https://raw.githubusercontent.com/statmike/bigquery-data-science/main/architectures/headers/icons/reddit.png" alt="Reddit Logo" width="20px"></a> 
    <a href="https://bsky.app/intent/compose?text=https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ai/RESOURCES.md"><img src="https://raw.githubusercontent.com/statmike/bigquery-data-science/main/architectures/headers/icons/bluesky.svg" alt="BlueSky Logo" width="20px"></a> 
    <a href="https://x.com/intent/post?url=https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ai/RESOURCES.md"><img src="https://raw.githubusercontent.com/statmike/bigquery-data-science/main/architectures/headers/icons/x.svg" alt="X (Twitter) Logo" width="20px"></a> 
  </td>
</tr>
<tr>
  <td style="text-align: right">
    <b>Connect With Author On: </b> 
    <a href="https://www.linkedin.com/in/statmike"><img src="https://raw.githubusercontent.com/statmike/bigquery-data-science/main/architectures/headers/icons/linkedin.svg" alt="Linkedin Logo" width="20px"></a>
    <a href="https://github.com/statmike"><img src="https://raw.githubusercontent.com/statmike/bigquery-data-science/main/architectures/headers/icons/github.svg" alt="GitHub Logo" width="20px"></a> 
    <a href="https://www.youtube.com/@statmike-channel"><img src="https://raw.githubusercontent.com/statmike/bigquery-data-science/main/architectures/headers/icons/youtube.svg" alt="YouTube Logo" width="20px"></a>
    <a href="https://bsky.app/profile/statmike.bsky.social"><img src="https://raw.githubusercontent.com/statmike/bigquery-data-science/main/architectures/headers/icons/bluesky.svg" alt="BlueSky Logo" width="20px"></a> 
    <a href="https://x.com/statmike"><img src="https://raw.githubusercontent.com/statmike/bigquery-data-science/main/architectures/headers/icons/x.svg" alt="X (Twitter) Logo" width="20px"></a>
  </td>
</tr>
<tr>
  <td style="text-align: right">
    <a href="https://raw.githubusercontent.com/statmike/bigquery-data-science/main/bigquery-ai/RESOURCES.md"><img src="https://raw.githubusercontent.com/statmike/bigquery-data-science/main/architectures/headers/icons/download.svg" alt="Download icon" width="20px"></a> <a href="https://raw.githubusercontent.com/statmike/bigquery-data-science/main/bigquery-ai/RESOURCES.md">Download File</a> <i>(right-click and "Save As")</i>
  </td>
</tr>
</table><br/><br/>

---
# BigQuery AI Functions Resources

BigQuery AI functions let you use generative AI, embeddings, search, forecasting, and tabular prediction directly within SQL queries. These functions span several categories: general-purpose text/multimodal generation, managed classification and scoring, embedding generation and semantic/hybrid search, and predictive AI (forecasting, anomaly detection, regression, and classification). They connect to Vertex AI models (Gemini, embedding models, TimesFM, TabFM, and third-party models) and can process structured data, text, images, audio, video, and PDFs -- all from within BigQuery SQL.

For each function we collect top level info. The documentation url is provided for each as a research retrieval page to help fill in this structure for each:
Function Name
- short description of type of function and what it does
- what this function can be used for examples
- documentation url:
- syntax
- inputs: list all possible inputs and combinations, calling out use of object refs and schemas
- outputs: list all possible outputs and their schemas (can be links)
- type: table valued, ....
- supported models: which gen ai models can be requested
- best practices
- limitations
- locations
- provisioned throughput usage

## Sections

- [Choosing a Gemini Model Endpoint](#choosing-a-gemini-model-endpoint) — which endpoint to name, and what the choice commits you to *(on this page)*
- **[General Purpose Functions](reference/general-purpose-functions.md)** — `AI.GENERATE` (including reusable column aliases for single-pass `STRUCT` unpacking) and its typed variants (`_BOOL`, `_DOUBLE`, `_INT`, `_TABLE`, `_TEXT`), `ML.GENERATE_TEXT`, and `AI.COUNT_TOKENS`
- **[Managed Functions](reference/managed-functions.md)** — `AI.IF`, `AI.SCORE`, `AI.CLASSIFY`, `AI.AGG`, `AI.TRANSLATE` — managed endpoints, no connection or model object to create
- **[Embedding Generation and Semantic Search](reference/embedding-generation-and-semantic-search.md)** — `AI.EMBED`, `AI.GENERATE_EMBEDDING` (including MaaS remote embedding models), `ML.GENERATE_EMBEDDING`, `AI.SIMILARITY`, `VECTOR_SEARCH`, `AI.SEARCH`, and hybrid search
- **[Predictive AI](reference/predictive-ai.md)** — `AI.FORECAST`, `AI.DETECT_ANOMALIES`, `AI.PREDICT`, `AI.EVALUATE` — the TimesFM and TabFM foundation models
- **[Augmented Analytics](reference/augmented-analytics.md)** — `AI.KEY_DRIVERS` — model-free contribution analysis, plus the pointer to `AI.CAUSAL_EFFECT`, which is [documented in `bigquery-ml`](../bigquery-ml/reference/model-free-functions.md#aicausal_effect) alongside the other causal estimators
- **[Document Processing](reference/document-processing.md)** — `AI.CHUNK_DOCUMENT`, `AI.PARSE_DOCUMENT`, and `ML.PROCESS_DOCUMENT` — zero-DDL layout-aware document chunking and structured layout parsing alongside specialized Document AI processor extraction
- **[Cloud AI Service Models](reference/cloud-ai-service-models.md)** — `ML.TRANSLATE`, `ML.UNDERSTAND_TEXT`, `ML.ANNOTATE_IMAGE`, `ML.TRANSCRIBE`, and `ML.PROCESS_DOCUMENT` — remote models over pre-trained Cloud AI services rather than Gemini, with the per-service API and IAM matrix and routing guidance against zero-DDL [`AI.TRANSLATE`](reference/managed-functions.md#aitranslate), [`AI.CHUNK_DOCUMENT`](reference/document-processing.md#aichunk_document), and [`AI.PARSE_DOCUMENT`](reference/document-processing.md#aiparse_document)
- **[Unstructured Data Infrastructure](reference/unstructured-data-infrastructure.md)** — object tables, the `OBJ.*` functions (including `OBJ.LIST`, the wildcard listing that returns ready `ObjectRef`s with no object table), the ObjectRef / ObjectRefRuntime schema reference, and the five call shapes (including `AI.CHUNK_DOCUMENT` and `AI.PARSE_DOCUMENT`) that consume `ObjectRef` values directly

---

## Choosing a Gemini Model Endpoint

Every generative function documents its supported models as "any GA or preview Gemini model." That is accurate but hides a few things worth knowing before you pick one. This section is the single place they are recorded; the per-function entries do not repeat them.

**The default is `gemini-3.5-flash-lite`.** Omit `endpoint` and that is what you get, on every function that takes the argument. Reading `full_response.model_version` (or `modelVersion` inside the raw Vertex JSON payload) on `AI.GENERATE` and `AI.GENERATE_BOOL` confirms `gemini-3.5-flash-lite` across unpinned runs. The default has moved before and nothing in the release notes announces it when it does, so an unpinned call is a different model from one month to the next. Every unpinned example in this project runs on the current default and its stored outputs reflect that model; pin `endpoint` whenever an output has to stay reproducible.

**Gemini 3.x and 4.x are the documented families.** The `AI.GENERATE` reference page lists three Gemini 4 endpoints and six Gemini 3.x endpoints as supported models (all resolve live):

| Endpoint | Launch Stage | Release Date | Typical Role |
|---|---|---|---|
| `gemini-4-hydrogen` | GA | `2026-11-12` | High-throughput Gemini 4 reasoning & structured extraction |
| `gemini-4-carbon` | GA | `2026-11-10` | Balanced Gemini 4 reasoning & synthesis |
| `gemini-4-argon` | GA | `2026-10-13` | Flagship Gemini 4 frontier reasoning (`preferred_defaults.pro`) |
| `gemini-3.8-flash` | GA | `2026-09-21` | Fast general-purpose multimodal generation (`preferred_defaults.flash`) |
| `gemini-3.5-flash-lite` | GA | `2026-09-09` | Default unpinned endpoint (`preferred_defaults.flash_lite`) |
| `gemini-3.7-flash` · `gemini-3.6-flash` · `gemini-3.5-flash` · `gemini-3.1-flash-lite` | GA | `2026-08`–`2026-09` | Earlier Gemini 3.x Flash / Flash-Lite variants (`gemini-3.1-flash-lite-preview` is retired) |

The 2.5 family -- `gemini-2.5-flash`, `gemini-2.5-pro`, `gemini-2.5-flash-lite` -- is no longer on that list but still resolves and returns its own `modelVersion`; `gemini-2.0-flash` does not (*"Unsupported endpoint: Publisher model ... was not found"*). The examples in this project that pin a Gemini endpoint standardize on `gemini-3.8-flash` (latest GA Flash) and `gemini-4-argon` (flagship GA Gemini 4 reasoning model, alongside `gemini-4-carbon` and `gemini-4-hydrogen`; note that `gemini-3.8-pro` and `gemini-3.5-pro` do not exist as publisher endpoints), while unpinned examples resolve to the current default (`gemini-3.5-flash-lite`). To pin an endpoint explicitly:

```sql
SELECT AI.GENERATE(('Summarize: ', body), endpoint => 'gemini-3.8-flash').result
FROM `PROJECT_ID.DATASET_ID.TABLE_ID`;
```

**Thinking controls differ by generation.** Gemini 2.5 takes `thinking_budget` inside `model_params.generation_config.thinking_config`; for Gemini 3.0 and later (`gemini-3.8-flash`, `gemini-4-argon`, `gemini-4-carbon`, `gemini-4-hydrogen`) the documented control is `thinking_level` (`LOW`, `MEDIUM`, `HIGH`) in the same place. Passing `thinking_budget` or `thinking_level` set to `"MINIMAL"` or `"XHIGH"` to a Gemini 4 endpoint in BigQuery SQL `model_params` is rejected with HTTP 400 (`Invalid model_params`), and Gemini 4 models silently ignore `temperature`, `top_p`, and `top_k`. `thinking_budget: 0` is still accepted on `gemini-3.5-flash` (measured), but write `thinking_level` (`LOW`, `MEDIUM`, or `HIGH`) for 3.x and 4.x.

**A naming note.** The reference pages now call the model host the **Gemini Enterprise Agent Platform** -- "Agent Platform" for short -- where they used to say Vertex AI. Endpoints, connections, IAM roles and the `aiplatform.googleapis.com` hostnames are unchanged; only the product name moved. This project adopts the new name as pages are touched.

**GOTCHA -- Gemini 3.x is multi-regional only.** Unlike the 2.5 family, the 3.x models are not served from regional endpoints, only from the `us`, `eu`, and global multi-regional endpoints. If you pass a short model name, BigQuery resolves the endpoint for you, and the rule is not obvious:

| Query location | Endpoint used |
|----------------|---------------|
| `us`, or any single US region | `us` |
| `eu`, or any single EU region **except** `europe-west2` / `europe-west6` | `eu` |
| Everything else, **including `europe-west2` and `europe-west6`** | global |

The two European exceptions matter: a query running in London (`europe-west2`) silently uses the **global** endpoint, where you cannot control or know which region processes the request. If you have data processing location requirements, that is a compliance problem, not a performance note. Pin the endpoint explicitly with a fully qualified multi-regional name to avoid it:

```
https://aiplatform.us.rep.googleapis.com/v1/projects/PROJECT_ID/locations/us/publishers/google/models/MODEL_ID
```

Also note for cost planning: in `asia-northeast1`, `asia-south1`, `asia-southeast1`, and `europe-west2`, Gemini 3.5 Flash supports only Single Zone Provisioned Throughput.
