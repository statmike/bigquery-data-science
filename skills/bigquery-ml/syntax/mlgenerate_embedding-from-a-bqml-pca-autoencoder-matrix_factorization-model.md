# `ML.GENERATE_EMBEDDING` (from a BQML PCA / AUTOENCODER / MATRIX_FACTORIZATION model)

> **Source:** [`bigquery-ml/reference/model-lifecycle-functions.md#mlgenerate_embedding-from-a-bqml-pca--autoencoder--matrix_factorization-model`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ml/reference/model-lifecycle-functions.md#mlgenerate_embedding-from-a-bqml-pca--autoencoder--matrix_factorization-model)

> **Scope note:** This entry covers ONLY the in-house BQML-model use of `ML.GENERATE_EMBEDDING` — extracting embeddings from a trained `PCA`, `AUTOENCODER`, or `MATRIX_FACTORIZATION` model. The **foundation/remote-model (text & multimodal) use** of `ML.GENERATE_EMBEDDING` / `AI.GENERATE_EMBEDDING` is owned by `../bigquery-ai/` — see that doc; do not duplicate here.

- **Description:** Produces a single `ARRAY<FLOAT>` embedding column from a trained BQML model, meant for use with `VECTOR_SEARCH`. The function delegates internally: PCA/autoencoder route through `ML.PREDICT`; matrix factorization routes through `ML.WEIGHTS`.
- **Use cases:**
  - Turn PCA principal-component projections into a single vector column for similarity search.
  - Extract autoencoder latent-space (bottleneck) representations as embeddings.
  - Extract matrix-factorization user/item factor weights as entity embeddings.
- **documentation:** https://cloud.google.com/bigquery/docs/reference/standard-sql/bigqueryml-syntax-generate-embedding
- **Type:** Table-valued function.
- **Applies to models:** `PCA`, `AUTOENCODER`, `MATRIX_FACTORIZATION` (this entry); plus remote/foundation embedding models (cross-link out).

**Syntax:**
```sql
SELECT *
FROM ML.GENERATE_EMBEDDING(
  MODEL `PROJECT_ID.DATASET.MODEL_NAME`,
  { TABLE `PROJECT_ID.DATASET.INPUT` | (QUERY_STATEMENT) }
  [, STRUCT(TRIAL_ID AS trial_id)]
);
```

**Inputs:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `MODEL` | model | Yes | — | A trained `PCA`, `AUTOENCODER`, or `MATRIX_FACTORIZATION` model. |
| `TABLE` / `QUERY_STATEMENT` | table/query | Yes | — | Input rows. For PCA/autoencoder, columns must match the model's training features. For matrix factorization, provide the user or item entities. |
| `trial_id` | INT64 | No | optimal trial | Select a specific HP-tuning trial (only when trained with HP tuning). |

**Outputs:**

| Column | Type | Description |
|--------|------|-------------|
| `ml_generate_embedding_result` | ARRAY\<FLOAT\> | The embedding. PCA: one element per principal component (set by `num_principal_components`, or variable when `pca_explained_variance_ratio` is used). AUTOENCODER: dimension = the middle (bottleneck) entry of `hidden_units`. MATRIX_FACTORIZATION: the factor weights plus the intercept/bias as the last element; length = `num_factors` (+1 for intercept). |
| `processed_input` | STRING | Matrix factorization only: the name of the user or item column the embedding represents. |
| `trial_id` | INT64 | Present only when the model was trained with HP tuning. |
| *(passthrough)* | — | Input columns are carried through alongside the embedding. |

**Best practices:**
- The single `ml_generate_embedding_result` column is purpose-built for `VECTOR_SEARCH` — keep it as the array and avoid unnesting before indexing.
- For autoencoders, the bottleneck size (middle of `hidden_units`) directly sets the embedding dimension — choose it deliberately at train time.
- `AI.GENERATE_EMBEDDING` is the newer simplified variant; it emits the result in an `embedding` column instead of `ml_generate_embedding_result`. Use `ML.GENERATE_EMBEDDING` when you need the granular PCA / matrix-factorization control.

**Limitations:**
- Embeddings reflect only what the underlying model learned (linear components for PCA; reconstruction-driven latents for autoencoders; collaborative factors for matrix factorization) — not semantic text/image meaning (use the foundation-model path for that).
- **Verified: `VECTOR_SEARCH` does NOT accept `ML.GENERATE_EMBEDDING`'s output passed directly as its base-table argument** — `VECTOR_SEARCH(ML.GENERATE_EMBEDDING(...), ...)` errors with `"Unsupported query pattern"` (`models/autoencoder/`). Materialize the embeddings into a real table (or view) first, then run `VECTOR_SEARCH` against that table. Also verified: `ML.GENERATE_EMBEDDING` does NOT normalize its output — the raw result is bit-for-bit identical to hand-computing the same values via `ML.PREDICT`'s latent/projection columns; if `VECTOR_SEARCH` uses `COSINE` distance, no separate `ML.NORMALIZER` step is needed (`COSINE` and manual-normalize+`DOT_PRODUCT` give mathematically identical rankings).
- Matrix-factorization embeddings are per-entity (user/item), not per-row feature embeddings.

**BigFrames API:** No direct single-call `generate_embedding` wrapper for these in-house model types; equivalent results come from `PCA.transform()`, the autoencoder `predict()` latent output, and `MatrixFactorization` weights via the respective `bigframes.ml` classes. (Foundation embeddings: `bigframes.ml.llm.TextEmbeddingGenerator` — cross-link out.)

**Repo example (tested):**
- `bigquery-ml/models/pca/pca.sql` (Example 8) — wraps the same projection Example 3 gets from `ML.PREDICT` into one `ml_generate_embedding_result ARRAY<FLOAT>` column. Verified: the array values match `ML.PREDICT`'s `principal_component_1/2` exactly, in order.
- `bigquery-ml/models/autoencoder/autoencoder.sql` (Example 9) — the same for the autoencoder latent space; the array matches `ML.PREDICT`'s `latent_col_*` exactly, in order. Example 10 then compares the manual route (`ML.PREDICT` → wrap into an ARRAY → optional `ML.NORMALIZER`) against the wrapper, feeding both into `VECTOR_SEARCH`.
- `bigquery-ml/models/matrix_factorization/matrix_factorization.sql` — the per-entity (user/item) case, used for item-item similarity via `VECTOR_SEARCH`.
- `bigquery-ml/functions/distance/distance.sql` — `ML.DISTANCE` as the brute-force alternative for a one-off pairwise comparison, without building a vector index.

The wrapper packages what `ML.PREDICT` already returns into a single array column purpose-built for `VECTOR_SEARCH`; the two are verified equivalent above, so choose by what consumes the output.


---
