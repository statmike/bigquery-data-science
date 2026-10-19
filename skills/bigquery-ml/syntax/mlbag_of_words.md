# `ML.BAG_OF_WORDS`

> **Source:** [`bigquery-ml/reference/model-free-functions.md#mlbag_of_words`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ml/reference/model-free-functions.md#mlbag_of_words)

- **Description:** Computes a bag-of-words (per-document term-frequency) representation of tokenized documents.
- **Use cases:**
  - Produce sparse count features for text classification when raw frequency (not IDF weighting) is wanted.
  - Quick baseline text features feeding `LOGISTIC_REG` / `BOOSTED_TREE_*`.
- **documentation:** https://cloud.google.com/bigquery/docs/reference/standard-sql/bigqueryml-syntax-bag-of-words
- **Type:** Analytic — **requires `OVER ()`** (dictionary is built across the document window).
- **Applies to models:** Any model type via `TRANSFORM` or precomputed columns.

**Syntax:**
```sql
ML.BAG_OF_WORDS(tokenized_document [, top_k] [, frequency_threshold]) OVER ()
```

**Inputs:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `tokenized_document` | `ARRAY<STRING>` | Yes | — | One document's tokens. |
| `top_k` | `INT64` | No | 32000 (max 1048576) | Dictionary size excluding the unknown term; keeps the `top_k` terms appearing in the most documents. |
| `frequency_threshold` | `INT64` | No | 5 | Minimum number of documents a term must appear in to enter the dictionary. |

**Outputs:**

| Column | Type | Description |
|--------|------|-------------|
| (result) | `ARRAY<STRUCT<index INT64, value INT64>>` | Per-document term counts. `index 0` = unknown term; remaining indices map to the alphabetically ordered dictionary; `value` is the count of that term in the document. |

**Best practices:** Use inside `TRANSFORM` so the dictionary is frozen with the model and re-applied at predict time. Combine with `ML.NGRAMS` upstream for n-gram bags. Use `top_k` to cap dimensionality.
**Limitations:** Empty `OVER ()` required; counts depend on the analytic window — apply over the full corpus. Index `0` reserved for unknown. Shares the same `frequency_threshold=5` default gotcha as `ML.TF_IDF` above — verified live (see that entry).
**BigFrames API:** No direct equivalent.
**Repo example (tested):** `bigquery-ml/functions/text/text.ipynb` — real product-name tokens, the `frequency_threshold=5` gotcha proof, and `ML.BAG_OF_WORDS` embedded in a real `LOGISTIC_REG` `TRANSFORM` classifying product category from the product name alone (~0.95 accuracy).

---

**Status:** All three are **GA**. **Connection required:** No.

**Typical pipeline:** tokenize (GoogleSQL `TEXT_ANALYZE`/`SPLIT`) → optional `ML.NGRAMS` → `ML.BAG_OF_WORDS`
or `ML.TF_IDF` (in `TRANSFORM`) → train classifier. Note: `ML.TF_IDF`/`ML.BAG_OF_WORDS` are analytic
(`OVER ()`) and an analytic function cannot be an argument of another analytic function — chain via
subqueries/CTEs, not nesting (consistent with the repo's note for `ML.STANDARD_SCALER` etc.).


---
