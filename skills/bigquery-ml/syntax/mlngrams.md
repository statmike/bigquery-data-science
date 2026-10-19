# `ML.NGRAMS`

> **Source:** [`bigquery-ml/reference/model-free-functions.md#mlngrams`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ml/reference/model-free-functions.md#mlngrams)

- **Description:** Given an array of token strings, returns an array of concatenated n-grams for the requested size range.
- **Use cases:**
  - Build word/character n-gram features from tokenized text before bag-of-words or TF-IDF.
  - Capture local token order (bigrams, trigrams) that single tokens lose.
- **documentation:** https://cloud.google.com/bigquery/docs/reference/standard-sql/bigqueryml-syntax-ngrams
- **Type:** Scalar (row-wise — no `OVER()` needed; operates within a single array).
- **Applies to models:** Any model type, via `TRANSFORM` or pre-computed input columns. Exportable in `TRANSFORM`.

**Syntax:**
```sql
ML.NGRAMS(array_input, range [, separator])
```

**Inputs:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `array_input` | `ARRAY<STRING>` | Yes | — | Tokens to merge into n-grams. |
| `range` | `ARRAY<INT64>` | Yes | — | `[min, max]` n-gram sizes. **Correction, verified live: `range` must always be an `ARRAY<INT64>` — a bare `INT64` (the docs' claimed "single int `x` means `[x, x]`" shorthand) errors outright** (`"Unable to coerce type INT64 to expected type ARRAY<INT64>"`). Use `[x, x]` explicitly for a single size. |
| `separator` | `STRING` | No | `' '` (space) | Joins adjacent tokens in each output n-gram. |

**Outputs:**

| Column | Type | Description |
|--------|------|-------------|
| (result) | `ARRAY<STRING>` | All n-grams within `range`, each a `separator`-joined string. |

**Best practices:** Keep `range` tight (e.g. `[1, 2]`) — wide ranges explode feature cardinality. Tokenize and lowercase upstream for consistency.
**Limitations:** Scalar over one array per row; does not aggregate across rows. Order is preserved from the input array.
**BigFrames API:** No direct equivalent (use SQL / `bigframes.bigquery` passthrough).
**Repo example (tested):** [`functions/text/`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ml/functions/text) — Example 1 tokenizes first (all three text functions require `ARRAY<STRING>`); Example 2 runs `ML.NGRAMS(tokens, [2, 3])` on a real tokenized product name (`SPLIT(LOWER('Low Profile Dyed Cotton Cap'), ' ')`) to produce bigrams and trigrams in one call.

---
