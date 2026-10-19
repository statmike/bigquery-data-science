# `ML.TRANSCRIBE`

> **Source:** [`bigquery-ai/reference/cloud-ai-service-models.md#mltranscribe`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ai/reference/cloud-ai-service-models.md#mltranscribe)

- **Description:** Table-valued function that transcribes audio in an object table with Speech-to-Text V2, returning the finished text in a `STRING` column.
- [documentation](https://cloud.google.com/bigquery/docs/reference/standard-sql/bigqueryml-syntax-transcribe) · [notebook](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ai/functions/ml_transcribe/ml_transcribe.ipynb) · [sql](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ai/functions/ml_transcribe/ml_transcribe.sql)

```sql
SELECT * FROM ML.TRANSCRIBE(
  MODEL `PROJECT_ID.DATASET.MODEL_NAME`,
  { TABLE `PROJECT_ID.DATASET.OBJECT_TABLE` | (QUERY_STATEMENT) },
  recognition_config => JSON '{"language_codes": ["en-US"], "model": "chirp", "auto_decoding_config": {}}');
```

**Output:** `transcripts` (`STRING` — the full transcript), `ml_transcribe_result` (JSON), `ml_transcribe_status`, plus the object table columns.

**Worth knowing:**
- **The third argument is a named argument, not a `STRUCT`** — the only member of the family that breaks the convention. It is also **required** unless the model was created with `SPEECH_RECOGNIZER`. Both mistakes produce errors that print the signature: `ML.TRANSCRIBE(MODEL, TABLE, [recognition_config => JSON])`.
- **`chirp` is the only accepted `model`.** `chirp_2`, `long`, `short` and `telephony` are all rejected with *"Supported models are: chirp."*
- **`SPEECH_RECOGNIZER` is regional.** BigQuery accepts a recognizer only from `asia-southeast1`, `us-central1` or `europe-west4` — a constraint to weigh against a multi-region dataset before choosing a recognizer over a per-call config.
- **`language_codes` is echoed, not enforced.** Forcing `["en-US"]` on French audio still returns French, still reporting `en-US`. `["auto"]` detects and reports bare subtags (`fr`, `es`, `en`).
- **Some `features` keys void the row.** `enable_automatic_punctuation` and `enable_word_time_offsets` work; `enable_word_confidence`, `diarization_config` and `profanity_filter` each fail the row with *"Config contains unsupported fields"* — naming no field, so you find the culprit by bisecting the object.
- **The result JSON is keyed by URI.** `ml_transcribe_result.results[uri]…` — the accessor has to index the JSON with the row's own `uri` column, and long audio arrives as several segments, which the `transcripts` column concatenates for you.
- **It is not reproducible.** Identical calls with the cache off can return different transcripts. Transcribe once, persist, and treat the text as data rather than as a key.

---
