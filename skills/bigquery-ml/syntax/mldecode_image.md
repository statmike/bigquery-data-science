# `ML.DECODE_IMAGE`

> **Source:** [`bigquery-ml/reference/model-free-functions.md#mldecode_image`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ml/reference/model-free-functions.md#mldecode_image)

- **Description:** Converts image bytes into a multi-dimensional `STRUCT` of dimensions + pixel values that downstream image functions and vision models consume. This is the required entry point of the image pipeline. The argument is **any `BYTES` value** — an object table's `data` pseudocolumn is the usual source, but a `FROM_BASE64(...)` literal or a `BYTES` table column works identically (verified).
- **Use cases:**
  - Decode JPEG/PNG/BMP bytes from an object table before inference with an imported/remote vision model.
  - Produce a reusable decoded-image column to feed `ML.RESIZE_IMAGE` / `ML.CONVERT_*`.
- **documentation:** [ML.DECODE_IMAGE](https://cloud.google.com/bigquery/docs/reference/standard-sql/bigqueryml-syntax-decode-image) · [Run inference on image object tables](https://cloud.google.com/bigquery/docs/object-table-inference)
- **Type:** Scalar (row-wise; no `OVER()`).
- **Applies to models:** Imported/remote vision models via `ML.PREDICT`, or any model's `TRANSFORM` that takes image input. Operates on object-table image bytes, not on a trained BQML model.

**Syntax:**
```sql
ML.DECODE_IMAGE(image_bytes)
```

**Inputs:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `image_bytes` | BYTES | Yes | — | Any `BYTES` value holding a JPEG/PNG/BMP image — typically an object table's `data` pseudocolumn. Must be `<= 10 MB`. |

**Outputs:**

| Column | Type | Description |
|--------|------|-------------|
| (result) | STRUCT\<ARRAY\<INT64\> dimensions, ARRAY\<FLOAT64\> values\> | Decoded image. `dimensions` is `[height, width, channels]`; `values` is `H × W × C` floats, **row-major HWC**, each `pixel / 255` on the **closed** interval `[0, 1]`. |

**Best practices:**
- When passing `ML.DECODE_IMAGE` output **directly** into `ML.PREDICT`, alias it with the model's expected input field name (e.g. `... AS input`).
- For repeated use, persist the decoded column to a table to avoid re-decoding.
**Limitations:**
- **Requires a reservation** — see the family gotcha above.
- **Channels is always 3.** Verified: an RGBA PNG comes back `[1, 2, 3]` with the alpha channel **dropped, not composited** (an `alpha = 128` pixel returns its raw RGB unchanged), and a single-channel grayscale PNG is **replicated into three identical channels**. There is no way to get 1 or 4 channels out of this function; do alpha compositing before the bytes reach BigQuery.
- The documented range `[0, 1)` is **wrong at the top end** — a pure-white pixel returns exactly `1.0` (verified). The interval is closed.
- Values are float64-exact: `values` matches `pixel / 255` computed in float64 with a maximum absolute difference of `0.0` (verified).
- Only JPEG, PNG, and BMP decode. Anything else — including a GIF, a WebP, or non-image bytes — fails with `Input image bytes could not be decoded. Expected valid image of type PNG, JPEG, or BMP; error in ML.DECODE_IMAGE expression`. `content_type` on an object table is upload-time metadata and is **not** validation; this error is the only real check.
- JPEG is lossy and is not close at small sizes: a 1×2 image of `(200,100,50),(0,128,255)` round-trips through JPEG as `(105,123,159),(86,104,140)` (Pillow's encoder at its default quality; a different encoder or quality gives different numbers, which is the point). PNG round-trips exactly. Use PNG for anything where pixel values matter.
- Large images can exceed editor display limits — write to a table.
**BigFrames API:** No direct equivalent (use SQL / object tables).
**Repo example (tested):** [`functions/image/`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ml/functions/image) — Steps 1–3 decode from `FROM_BASE64` literals and prove the field names, the channel rule, the closed range, the format list, and JPEG loss; Step 8 runs the object-table `data` path end to end.

---
