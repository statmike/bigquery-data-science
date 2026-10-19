# `ML.TF_IDF`

> **Source:** [`bigquery-ml/reference/model-free-functions.md#mltf_idf`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ml/reference/model-free-functions.md#mltf_idf)

- **Description:** Computes term frequency–inverse document frequency relevance scores for terms across a set of tokenized documents.
- **Use cases:**
  - Weight terms by importance (frequent-in-doc but rare-across-corpus) for sparse text features.
  - Feed sparse TF-IDF vectors to linear / logistic regression (`LINEAR_REG`, `LOGISTIC_REG`) for text classification.
- **documentation:** https://cloud.google.com/bigquery/docs/reference/standard-sql/bigqueryml-syntax-tf-idf
- **Type:** Analytic — **requires `OVER ()`** (IDF is computed across the whole window of documents).
- **Applies to models:** Any model type via `TRANSFORM` or precomputed columns.

**Syntax:**
```sql
ML.TF_IDF(tokenized_document [, top_k] [, frequency_threshold]) OVER ()
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
| (result) | `ARRAY<STRUCT<index INT64, value FLOAT64>>` | TF-IDF score per dictionary term for the document. `index 0` = unknown term (tokens not in dictionary); remaining indices map to the dictionary ordered alphabetically. |

**Best practices:** Same `top_k` / `frequency_threshold` across train and serve (use inside `TRANSFORM` so the dictionary is fixed in the model). Drop rare/noise terms via `frequency_threshold`.
**Limitations:** Must use empty `OVER ()`; the dictionary is built over the analytic window, so apply over the full training corpus. Index `0` always reserved for unknown. **MAJOR GOTCHA, verified live — shares the exact same `frequency_threshold=5` default trap as `ML.ONE_HOT_ENCODER`/`ML.LABEL_ENCODER` (see that entry):** on a small corpus, any term appearing in fewer than 5 documents collapses into the unknown bucket (index `0`), indistinguishable from a truly unseen term — tested with 6 tiny documents where a word appearing in 2 different documents was still indistinguishable from a word appearing in only 1.
**BigFrames API:** No direct equivalent.
**Repo example (tested):** `bigquery-ml/functions/text/text.ipynb` — real product-name tokens from `thelook_ecommerce.products`, the `frequency_threshold=5` gotcha proof above (tested directly for `ML.TF_IDF` itself, not just asserted by analogy to `ML.BAG_OF_WORDS`), and a concrete `ML.BAG_OF_WORDS`-vs-`ML.TF_IDF` contrast showing a term appearing in every document gets a *lower* TF-IDF weight than rarer terms, while BOW gives them identical raw counts.

---
