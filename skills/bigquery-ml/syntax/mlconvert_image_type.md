# `ML.CONVERT_IMAGE_TYPE`

> **Source:** [`bigquery-ml/reference/model-free-functions.md#mlconvert_image_type`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ml/reference/model-free-functions.md#mlconvert_image_type)

- **Description:** Converts the floating-point pixel values produced by `ML.DECODE_IMAGE` into integers on the **closed** range `[0, 255]`, as required by some models.
- **Use cases:**
  - Feed integer-input vision models (e.g. SSD MobileNet V2, which expects `tf.uint8`).
- **documentation:** [ML.CONVERT_IMAGE_TYPE](https://cloud.google.com/bigquery/docs/reference/standard-sql/bigqueryml-syntax-convert-image-type)
- **Type:** Scalar (row-wise; no `OVER()`).
- **Applies to models:** Same as the family; consumes `ML.DECODE_IMAGE` (or other image-function) output.

**Syntax:**
```sql
ML.CONVERT_IMAGE_TYPE(decoded_image)
```

**Inputs:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `decoded_image` | STRUCT with `ARRAY<FLOAT64> values` | Yes | — | Image whose float pixel values are converted to integers on `[0, 255]`. **Only the float form is accepted** — see below. |

**Outputs:**

| Column | Type | Description |
|--------|------|-------------|
| (result) | STRUCT\<ARRAY\<INT64\> dimensions, ARRAY\<INT64\> values\> | Image with integer pixel values. |

**Best practices:** Apply only when the target model requires integer pixels; leave float output for models trained on `[0,1]` floats. Make it the **last** step of the pipeline — `ML.RESIZE_IMAGE` is type-preserving and will re-quantize integers at every subsequent resize.
**Limitations:**
- **Requires a reservation** — see the family gotcha above.
- **It is one-way.** There is no inverse and no overload for integer input; feeding it its own output fails with `No matching signature for function ML.CONVERT_IMAGE_TYPE / Argument types: STRUCT<dimensions ARRAY<INT64>, values ARRAY<INT64>> / Signature: ML.CONVERT_IMAGE_TYPE(STRUCT<dimensions ARRAY<INT64>, values ARRAY<FLOAT64>>)`. (That error is also the authoritative statement of the struct's field names.)
- The documented range `[0, 255)` is **wrong at the top end** — a pure-white pixel returns exactly `255` (verified). The interval is closed.
- Matches `tf.image.convert_image_dtype(..., tf.uint8)` exactly (verified against TensorFlow 2.21.0).
- Output-size/display gotcha as above.
**BigFrames API:** No direct equivalent.
**Repo example (tested):** [`functions/image/`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ml/functions/image) Steps 3–4 — the closed range, the one-way signature error, and the pipeline-ordering consequence; Step 8 ends its feature pipeline with it.

---
