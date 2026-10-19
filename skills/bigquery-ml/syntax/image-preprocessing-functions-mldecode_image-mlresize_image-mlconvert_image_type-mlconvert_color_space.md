# Image preprocessing functions: `ML.DECODE_IMAGE`, `ML.RESIZE_IMAGE`, `ML.CONVERT_IMAGE_TYPE`, `ML.CONVERT_COLOR_SPACE`

> **Source:** [`bigquery-ml/reference/model-free-functions.md#image-preprocessing-functions-mldecode_image-mlresize_image-mlconvert_image_type-mlconvert_color_space`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ml/reference/model-free-functions.md#image-preprocessing-functions-mldecode_image-mlresize_image-mlconvert_image_type-mlconvert_color_space)

These four model-free functions form the image-preprocessing pipeline in BigQuery ML
[manual preprocessing](https://cloud.google.com/bigquery/docs/manual-preprocessing). They turn
image bytes stored in an [object table](https://cloud.google.com/bigquery/docs/object-tables) into the
multi-dimensional numeric `STRUCT` representation that an imported/remote vision model expects. They can
be used directly inside `ML.PREDICT`, written to an intermediate table column, or placed inside the
[`TRANSFORM`](https://cloud.google.com/bigquery/docs/reference/standard-sql/bigqueryml-syntax-create#transform)
clause of `CREATE MODEL` so the preprocessing re-applies automatically at prediction time.

> **Pipeline order:** `ML.DECODE_IMAGE` is always the entry point (bytes → image `STRUCT`). Its output
> feeds `ML.RESIZE_IMAGE`, `ML.CONVERT_IMAGE_TYPE`, and/or `ML.CONVERT_COLOR_SPACE` in any combination,
> e.g. `ML.CONVERT_COLOR_SPACE(ML.RESIZE_IMAGE(ML.DECODE_IMAGE(data), 224, 280, TRUE), 'YIQ')`.
> All four are **scalar, row-wise** functions — no `OVER()` clause (they operate on a single image per
> row, not on statistics across rows), so they nest freely inside one another and inside `TRANSFORM`.

> **Scope note:** These are BQML preprocessing primitives for *running a vision model on image bytes*
> (in-scope here). The foundation-model multimodal path — `ML.ANNOTATE_IMAGE`, multimodal
> `ML.GENERATE_TEXT`/`AI.GENERATE_*` over images — is owned by `../bigquery-ai/`; cross-link there,
> do not duplicate.

> **RESERVATION GOTCHA (all four) — verified live, undocumented.** These functions **cannot run under
> on-demand (per-byte) pricing**. Every one of them fails with:
> `BigQuery's ML image-processing functions requires reservation, but no reservation was assigned for job type `QUERY`, to project `<project>` or its parent, in location `<location>`.`
> None of the four reference pages says this, and neither do the
> [manual preprocessing](https://cloud.google.com/bigquery/docs/manual-preprocessing) or
> [object table inference](https://cloud.google.com/bigquery/docs/object-table-inference) pages that
> tell you to use them. `MATRIX_FACTORIZATION` is the only other thing in this project with the same
> requirement. The fix is a small **`ENTERPRISE` autoscale reservation** (0 baseline slots) — not a
> capacity commitment. `functions/image/` creates one in Setup and deletes it in Cleanup.
> **Assignment propagation is not atomic** — verified: after a fixed 90-second wait a probe query
> succeeded and the very next query, seconds later, failed with the identical error. Wait on several
> consecutive successes, not on a clock.

> **Output-size gotcha (all four):** referencing these functions directly in the BigQuery editor can
> fail to display; write results to a table instead. The documented hard limits are `<= 10 MB`
> (10,000,000 bytes) for the `BYTES` value passed to `ML.DECODE_IMAGE`, and `< 20 MB` per object-table
> image file (JPEG/PNG/BMP, total `< 1 TB`). The decoded `STRUCT`'s **60 MB ceiling is not a hard
> limit** — the docs say a struct larger than 60 MB "is downscaled to that size while preserving
> aspect ratio," i.e. a silently resized input rather than a failed query. (Not exercised in
> `functions/image/`, whose images are a few pixels each.) Pin large images with an explicit
> `ML.RESIZE_IMAGE` rather than relying on that ceiling.

> **The struct's fields are `dimensions` and `values`** — verified against the engine's own signature
> error text. `dimensions` is `[height, width, channels]`; `values` is flattened **row-major in HWC
> order**. The reference pages leave the fields unnamed (`STRUCT<ARRAY<INT64>, ARRAY<FLOAT64>>`);
> earlier revisions of this file guessed `shape`, and selecting `.shape` errors.

> **All four are TensorFlow image ops.** Diffed live against TensorFlow 2.21.0 in `functions/image/`:
> `ML.CONVERT_COLOR_SPACE(..., 'HSV')` and `ML.RESIZE_IMAGE` (bilinear) match `tf.image.rgb_to_hsv` and
> `tf.image.resize` **bit-exactly**; `YIQ`/`YUV` match `tf.image.rgb_to_yiq`/`rgb_to_yuv` to one ULP of
> a double; `'GRAYSCALE'` is the one row that differs, by ~1.6e-8, because `tf.image.rgb_to_grayscale`
> casts to **float32** before applying the weights (`convert_image_dtype(images, dtypes.float32)` in its
> source) while BigQuery stays in double — apply the same weights in float64 and the gap collapses to one
> ULP. Where these pages are silent or wrong — channel count, range endpoints, rounding rule,
> luma weights, interpolation convention — **`tf.image`'s documented behavior is the answer**.
> **If you run this diff yourself, pin the reference tensor** with `tf.constant(x, tf.float64)`: handing
> `tf.image` a bare NumPy `float64` array can return float32, which manufactures a ~1e-8 "finding" out of
> a bit-exact function.

---
