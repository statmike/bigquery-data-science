# What the five have in common

> **Source:** [`bigquery-ai/reference/cloud-ai-service-models.md#what-the-five-have-in-common`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ai/reference/cloud-ai-service-models.md#what-the-five-have-in-common)

**A model object that is a handle, not a model.** Every member needs `CREATE MODEL … REMOTE WITH CONNECTION … OPTIONS(REMOTE_SERVICE_TYPE = …)` first. Nothing trains and no data is read:

```sql
CREATE OR REPLACE MODEL `PROJECT_ID.DATASET.MODEL_NAME`
  REMOTE WITH CONNECTION `PROJECT_ID.REGION.CONNECTION_ID`
  OPTIONS (REMOTE_SERVICE_TYPE = 'CLOUD_AI_VISION_V1');
```

The model's own metadata says as much: `model_type` is unspecified, the single training run carries an empty `trainingOptions` and an empty `evaluationMetrics`, and the only substance in the record is `remoteModelInfo`. Each notebook prints it in its last SQL example.

**`ML.EVALUATE` is rejected.** Asking for it returns *"ML.EVALUATE is not supported for remote models on Cloud AI APIs."* There is nothing to evaluate — the service is the model, and its quality is Google's version number, not your training run.

**Models are not in `INFORMATION_SCHEMA`.** `INFORMATION_SCHEMA.TABLES` lists object tables but no models, and this project has no `INFORMATION_SCHEMA.MODELS` view. Read model metadata through the client library (`client.get_model(...).to_api_repr()`) or `bq show --model`.

**Three output columns, named after the function.** Each returns the input columns plus `<function>_result` (`JSON`) and `<function>_status` (`STRING`, empty on success). `ML.TRANSCRIBE` adds a fourth, `transcripts` (`STRING`) — the only member that hands back a finished answer without a JSON accessor.

**Failures are per row.** A row that the service rejects fills `<function>_status` and leaves the result empty **while the job succeeds**. A pipeline that does not select the status column records the failure as a result. See [Per-row failures](per-row-failures-and-the-retry-pattern.md).

**They run on on-demand pricing.** Measured for `ML.TRANSCRIBE` in `INFORMATION_SCHEMA.JOBS_BY_PROJECT`: every call reports no `reservation_id` and an `edition` of `none` — on-demand. No BigQuery Editions reservation is required — unlike the [image preprocessing functions](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ml/reference/model-free-functions.md#image-preprocessing-functions-mldecode_image-mlresize_image-mlconvert_image_type-mlconvert_color_space) in the sibling `bigquery-ml` project, which fail outright without one. The BigQuery bill is bytes scanned; the service bill is separate and is priced by the service's own unit — characters for Translation and Natural Language, images (and features per image) for Vision, **seconds of audio** for Speech-to-Text, pages for Document AI.

**They are the stable option.** Nothing about their output moves when a Gemini default changes. That is the reason to choose them over an `AI.*` function with a prompt, and it is not the same as being deterministic — `ML.TRANSCRIBE` disagrees with itself across identical calls, while `ML.TRANSLATE` and `ML.UNDERSTAND_TEXT` do not. Each notebook measures this directly with the query cache off.

---
