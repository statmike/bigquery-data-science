# Per-row failures and the retry pattern

> **Source:** [`bigquery-ai/reference/cloud-ai-service-models.md#per-row-failures-and-the-retry-pattern`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ai/reference/cloud-ai-service-models.md#per-row-failures-and-the-retry-pattern)

Every member reports failure in a status column while the **job succeeds**. Measured examples: a non-audio file in a `ML.TRANSCRIBE` object table, and an unsupported language in `ML.UNDERSTAND_TEXT`. The standard shape is to persist results and re-run only the failures:

```sql
CREATE OR REPLACE TABLE `PROJECT_ID.DATASET.results` AS
SELECT * FROM ML.TRANSCRIBE(MODEL ..., TABLE ..., recognition_config => JSON '...');

-- what failed, and why
SELECT uri, ml_transcribe_status
FROM `PROJECT_ID.DATASET.results`
WHERE ml_transcribe_status != '';
```

Whether the retry can succeed depends on the cause: a `RESOURCE EXHAUSTED` row failed for load and will likely pass on a second attempt; a row that failed for an unsupported language or an unsupported encoding will fail identically forever. Read the status before retrying.

---
