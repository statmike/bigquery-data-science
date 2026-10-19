# Two input shapes

> **Source:** [`bigquery-ai/reference/cloud-ai-service-models.md#two-input-shapes`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ai/reference/cloud-ai-service-models.md#two-input-shapes)

**Object tables** — `ML.ANNOTATE_IMAGE`, `ML.TRANSCRIBE`, `ML.PROCESS_DOCUMENT`. An [object table](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ai/reference/unstructured-data-infrastructure.md) is an external table whose rows are files. It reads through the same connection, which is why the service account needs `roles/storage.objectViewer`:

```sql
CREATE OR REPLACE EXTERNAL TABLE `PROJECT_ID.DATASET.OBJECT_TABLE`
  WITH CONNECTION `PROJECT_ID.REGION.CONNECTION_ID`
  OPTIONS (object_metadata = 'SIMPLE', uris = ['gs://BUCKET/PREFIX/*']);
```

**A `text_content` column** — `ML.TRANSLATE`, `ML.UNDERSTAND_TEXT`. Both read a column named exactly `text_content`. A table without one errors, and the fix is an alias in a subquery rather than a rename of your table:

```sql
FROM ML.TRANSLATE(
  MODEL `PROJECT_ID.DATASET.MODEL_NAME`,
  (SELECT review_id, comment AS text_content FROM `PROJECT_ID.DATASET.reviews`),
  STRUCT('TRANSLATE_TEXT' AS translate_mode, 'en' AS target_language_code))
```

---
