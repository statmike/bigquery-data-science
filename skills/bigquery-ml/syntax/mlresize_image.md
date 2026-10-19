# `ML.RESIZE_IMAGE`

> **Source:** [`bigquery-ml/reference/model-free-functions.md#mlresize_image`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ml/reference/model-free-functions.md#mlresize_image)

- **Description:** Resizes a decoded image to a target height/width, optionally preserving aspect ratio.
- **Use cases:**
  - Match the fixed input resolution a vision model was trained on (e.g. 224×224).
  - Downscale large images to bound the decoded `STRUCT` size.
- **documentation:** [ML.RESIZE_IMAGE](https://cloud.google.com/bigquery/docs/reference/standard-sql/bigqueryml-syntax-resize-image)
- **Type:** Scalar (row-wise; no `OVER()`).
- **Applies to models:** Same as the family — `ML.PREDICT` input or `TRANSFORM`; consumes `ML.DECODE_IMAGE` output.

**Syntax:**
```sql
ML.RESIZE_IMAGE(decoded_image, target_height, target_width, preserve_aspect_ratio)
```

**Inputs:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `decoded_image` | STRUCT (from `ML.DECODE_IMAGE`) | Yes | — | The decoded image to resize. |
| `target_height` | INT64 | Yes | — | Target height in pixels (max height if `preserve_aspect_ratio = TRUE`). |
| `target_width` | INT64 | Yes | — | Target width in pixels (max width if `preserve_aspect_ratio = TRUE`). |
| `preserve_aspect_ratio` | BOOL | Yes | — | If `TRUE`, the two targets are a **bounding box, not a size**: scale = `min(target_h / h, target_w / w)`, and each output dimension is that scale times the source rounded **half-to-even**. |

**Outputs:**

| Column | Type | Description |
|--------|------|-------------|
| (result) | STRUCT (same form as input image) | The resized image. **Type-preserving**: `FLOAT64` in → `FLOAT64` out, `INT64` in → `INT64` out. |

**Best practices:**
- Resize to the model's exact expected dimensions; use `preserve_aspect_ratio = TRUE` when distortion would hurt accuracy — but read the bounding-box rule above, because `TRUE` does not give you the size you asked for.
- **Resize before `ML.CONVERT_IMAGE_TYPE`, not after.** Resize is type-preserving, so integers in means integers out and every resize step re-quantizes (verified: a 1×2 → 1×1 fit whose true blue-channel mean is `152.5` returns `152`, half-to-even). Keep the pipeline in floats and convert last.
**Limitations:**
- **Requires a reservation** — see the family gotcha above.
- **It returns float32-precision values**, unlike decode and color-space conversion, which are float64-exact. Verified: `16/255` comes back as `0.062745101749897`, exactly `float32(16/255)`. Do not diff resize output against a float64 reference and expect zero.
- **A degenerate aspect-preserved fit fails with an internal error, deterministically.** Whenever `min(target_h / h, target_w / w)` scales either source dimension below `0.5` — i.e. rounds it to zero — the query fails with `An internal error occurred ... Error: 80038528`. Verified on two differently-shaped sources; the same target size on the same image succeeds when the fit is non-degenerate, so it is the rounding-to-zero and not the small target. The message's "usually caused by a transient issue" is misleading here: **`google-cloud-bigquery`'s default job-retry believes it and resubmits for minutes.** Pass `job_retry=None`, and guard the input with `min(th/h, tw/w) * min(h, w) >= 0.5` or use `FALSE`.
- The exception class varies run to run for that same failure — `InternalServerError` (500) and `BadRequest` (400) have both been observed, and the 400 form omits the `Error: 80038528` code. Catch `GoogleAPICallError` and read `job.error_result['message']`.
- Output-size/display gotcha as above; takes a decoded image (chain after `ML.DECODE_IMAGE`).
**BigFrames API:** No direct equivalent.
**Repo example (tested):** [`functions/image/`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ml/functions/image) Step 6 — the bounding-box rounding table, the float32 finding, type preservation, and the deterministic internal error; Step 8 uses it in the object-table pipeline.

---
