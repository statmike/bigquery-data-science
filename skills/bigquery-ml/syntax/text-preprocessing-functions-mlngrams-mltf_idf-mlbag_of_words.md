# Text preprocessing functions: `ML.NGRAMS`, `ML.TF_IDF`, `ML.BAG_OF_WORDS`

> **Source:** [`bigquery-ml/reference/model-free-functions.md#text-preprocessing-functions-mlngrams-mltf_idf-mlbag_of_words`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ml/reference/model-free-functions.md#text-preprocessing-functions-mlngrams-mltf_idf-mlbag_of_words)

These three model-free functions turn tokenized text (an `ARRAY<STRING>` of tokens) into ML
features. They are part of BigQuery ML [manual preprocessing](https://cloud.google.com/bigquery/docs/manual-preprocessing)
and can be used standalone in SQL or inside the [`TRANSFORM`](https://cloud.google.com/bigquery/docs/reference/standard-sql/bigqueryml-syntax-create#transform)
clause of `CREATE MODEL` (so they re-apply automatically at `ML.PREDICT` time). They all operate
on pre-tokenized input — produce tokens first with GoogleSQL text functions such as
[`ML.BAG_OF_WORDS` upstream tokenizers](https://cloud.google.com/bigquery/docs/reference/standard-sql/text-analysis-functions)
(e.g. `BAG_OF_WORDS`, `TEXT_ANALYZE`) or simple `SPLIT(...)`.

> NUANCE: BigQuery also has same-named **text-analysis** functions (`TF_IDF`, `BAG_OF_WORDS`) under
> GoogleSQL — those return term strings as the dictionary index and order by frequency. The `ML.*`
> versions documented here return integer dictionary indices, order the dictionary alphabetically,
> and reserve index `0` for the unknown term. Use the `ML.*` versions for feature engineering / `TRANSFORM`.

---
