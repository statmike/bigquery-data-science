# `ML.CONVERT_COLOR_SPACE`

> **Source:** [`bigquery-ml/reference/model-free-functions.md#mlconvert_color_space`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ml/reference/model-free-functions.md#mlconvert_color_space)

- **Description:** Converts an RGB image to a different color space.
- **Use cases:**
  - Match the color space a vision model was trained on (e.g. grayscale or YIQ input).
- **documentation:** [ML.CONVERT_COLOR_SPACE](https://cloud.google.com/bigquery/docs/reference/standard-sql/bigqueryml-syntax-convert-color-space)
- **Type:** Scalar (row-wise; no `OVER()`).
- **Applies to models:** Same as the family; consumes `ML.DECODE_IMAGE`/`ML.RESIZE_IMAGE` output (input must be RGB).

**Syntax:**
```sql
ML.CONVERT_COLOR_SPACE(rgb_image, target_color_space)
```

**Inputs:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `rgb_image` | STRUCT (RGB, from `ML.DECODE_IMAGE`/`ML.RESIZE_IMAGE`) | Yes | — | Image in RGB color space. Accepts **either** value type — `ARRAY<FLOAT64>` or the `ARRAY<INT64>` produced by `ML.CONVERT_IMAGE_TYPE`. |
| `target_color_space` | STRING | Yes | — | Target color space: `'HSV'`, `'YIQ'`, `'YUV'`, or `'GRAYSCALE'`. |

**Outputs:**

| Column | Type | Description |
|--------|------|-------------|
| (result) | STRUCT\<ARRAY\<INT64\> dimensions, ARRAY\<FLOAT64\> values\> | Image in the requested color space. Always `FLOAT64`, whichever value type went in. `'GRAYSCALE'` returns **1 channel**; the other three return 3. |

**Best practices:** Only convert when the model expects a non-RGB color space; input must be RGB.
**Limitations:**
- **Requires a reservation** — see the family gotcha above.
- **`'GRAYSCALE'` changes the channel count to 1** (verified: a 1×2 RGB image converts to `[1, 2, 1]`, two values). This is the reverse of `ML.DECODE_IMAGE`, which replicates a grayscale source *up* to 3 channels — so a decode-then-grayscale pipeline goes 1 → 3 → 1, and the channel count of a feature vector is set by the last function in the chain, not by the source image. `'HSV'`, `'YIQ'`, and `'YUV'` return 3 distinct channels.
- **`'GRAYSCALE'` and `'YIQ'`'s Y channel are two different lumas.** `'GRAYSCALE'` uses `[0.2989, 0.5870, 0.1140]` — the 4-decimal rounding `tf.image.rgb_to_grayscale` hardcodes. `'YIQ'`'s Y uses the true BT.601 `[0.299, 0.587, 0.114]`. On RGB `(200, 100, 50)` they give `0.48698039215686273` and `0.4870588235294117`, a gap of `0.02` of one 8-bit level. Invisible, and enough to break a bit-for-bit reproducibility check against a reimplementation — pick the right one deliberately.
- **`'HSV'`'s hue is on `[0, 1]`, not degrees.** `(200, 100, 50)` → hue `0.05555555555555555`, which is 20°/360. A threshold written in degrees is off by 360×.
- **Integer input is normalized, not misread.** `ML.CONVERT_COLOR_SPACE(ML.CONVERT_IMAGE_TYPE(img), 'HSV')` is bit-identical to the float path — it divides by 255 on the way in rather than treating a `200` as already-scaled.
- An unsupported target is rejected by name: `Color space LAB is not supported; error in ML.CONVERT_COLOR_SPACE expression`.
- Output-size/display gotcha as above.
**BigFrames API:** No direct equivalent.
**Repo example (tested):** [`functions/image/`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ml/functions/image) Step 5 — the channel-count change, the two lumas, the `[0, 1]` hue, integer normalization, and the rejected target; Step 7 diffs `'HSV'`/`'YIQ'`/`'YUV'` against TensorFlow.

---

**Status:** All four are **GA**. **Reservation required: YES** — see the family gotcha at the top of this section; this is the one thing about them that no official page states. **Connection required:** No for the functions themselves; the *object table* over the image files needs a Cloud Resource Connection whose service account holds `roles/storage.objectViewer` on the bucket, and the vision model may need one too (see the model entry).

**TRANSFORM-clause behavior:** All four are exportable preprocessing functions usable inside `TRANSFORM`, so the decode/resize/type/color-space steps are stored with the model and re-applied automatically at `ML.PREDICT`. Because they are scalar (no `OVER()`), they nest directly and impose no analytic-window constraints — unlike the analytic scalers/encoders/text functions documented in this folder.

**Typical pipeline:** object table (`data` BYTES) → `ML.DECODE_IMAGE` → `ML.RESIZE_IMAGE` → `ML.CONVERT_COLOR_SPACE` → `ML.CONVERT_IMAGE_TYPE` → vision model via `ML.PREDICT` (or all of it inside `TRANSFORM`). **The order is not arbitrary:** `ML.CONVERT_IMAGE_TYPE` is one-way and has no integer→float signature, and `ML.RESIZE_IMAGE` is type-preserving, so converting early quantizes at every later resize. Convert last.

**Sources:** [ML.DECODE_IMAGE](https://cloud.google.com/bigquery/docs/reference/standard-sql/bigqueryml-syntax-decode-image) · [ML.RESIZE_IMAGE](https://cloud.google.com/bigquery/docs/reference/standard-sql/bigqueryml-syntax-resize-image) · [ML.CONVERT_IMAGE_TYPE](https://cloud.google.com/bigquery/docs/reference/standard-sql/bigqueryml-syntax-convert-image-type) · [ML.CONVERT_COLOR_SPACE](https://cloud.google.com/bigquery/docs/reference/standard-sql/bigqueryml-syntax-convert-color-space) · [Run inference on image object tables](https://cloud.google.com/bigquery/docs/object-table-inference)


---
