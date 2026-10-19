# `ML.ANNOTATE_IMAGE`

> **Source:** [`bigquery-ai/reference/cloud-ai-service-models.md#mlannotate_image`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ai/reference/cloud-ai-service-models.md#mlannotate_image)

- **Description:** Table-valued function that annotates images in an object table with the Cloud Vision API. One model serves every feature; the feature list is an argument to the function, not an option on the model.
- [documentation](https://cloud.google.com/bigquery/docs/reference/standard-sql/bigqueryml-syntax-annotate-image) · [notebook](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ai/functions/ml_annotate_image/ml_annotate_image.ipynb) · [sql](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ai/functions/ml_annotate_image/ml_annotate_image.sql)

```sql
SELECT * FROM ML.ANNOTATE_IMAGE(
  MODEL `PROJECT_ID.DATASET.MODEL_NAME`,
  { TABLE `PROJECT_ID.DATASET.OBJECT_TABLE` | (QUERY_STATEMENT) },
  STRUCT(['LABEL_DETECTION', 'OBJECT_LOCALIZATION'] AS vision_features));
```

The syntax page lists eight features: `LABEL_DETECTION`, `OBJECT_LOCALIZATION`, `TEXT_DETECTION`, `DOCUMENT_TEXT_DETECTION`, `LANDMARK_DETECTION`, `LOGO_DETECTION`, `FACE_DETECTION` and `IMAGE_PROPERTIES`.

**Output:** `ml_annotate_image_result` (JSON), `ml_annotate_image_status`, plus the object table columns.

**Worth knowing:**
- **One call, many features.** Requesting several features in one call is one pass over the image; the result JSON gains a top-level key per feature.
- **What the documented list covers and what the function parses are different sets.** Measured against the undocumented names: `SAFE_SEARCH_DETECTION` and `CROP_HINTS` are accepted and return `safe_search_annotation` and `crop_hints_annotation`; `WEB_DETECTION` is accepted and returns no keys at all; an invented name is rejected outright with `Found unsupported value … of setting field vision_features`. Accepted is not the same as supported — the silent-empty case is the one to guard against.
- **A zero-valued JSON field is omitted from the response.** Landmark bounding boxes are in absolute pixels, and a vertex at the origin arrives as `{}`, so `INT64(vertex.x)` returns `NULL` rather than `0`. Coalesce it.

---
