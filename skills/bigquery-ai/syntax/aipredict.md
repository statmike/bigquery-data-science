# `AI.PREDICT`

> **Source:** [`bigquery-ai/reference/predictive-ai.md#aipredict`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ai/reference/predictive-ai.md#aipredict)

- **Description:** (Preview) Table-valued function that performs zero-shot regression and classification on structured data using TabFM, Google's pre-trained tabular foundation model. You pass a labeled training table and an unlabeled prediction table in a single call; the model learns in context. There is no `CREATE MODEL`, no training job, no connection, no endpoint, and no persisted model object.
- **Use cases:** Predicting a numeric or categorical column without building a model, filling in missing structured attributes, quick baselines before investing in a trained model, prediction inside an analytics pipeline where a model artifact would be overhead.
- [documentation](https://docs.cloud.google.com/bigquery/docs/reference/standard-sql/bigqueryml-syntax-ai-predict)
- **Type:** Table-valued function (TVF) -- Preview

**Syntax:**
```sql
AI.PREDICT(
  { TABLE TRAINING_TABLE | (TRAINING_QUERY) },
  { TABLE PREDICTION_TABLE | (PREDICTION_QUERY) }
  [, label_col => 'LABEL_COL' ]
)
```

**Inputs:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `TRAINING_TABLE` / `TRAINING_QUERY` | Table/Query | Required | -- | Labeled training data. Must contain the label column; **every other column is treated as a feature**. |
| `PREDICTION_TABLE` / `PREDICTION_QUERY` | Table/Query | Required | -- | Rows to predict. Must contain all training feature columns; extra columns are allowed. |
| `label_col` | Named arg, STRING | Optional | `'label'` | Name of the label column in the training data. A column literally named `label` needs no argument. |

Feature and label columns must be `STRING`, `BOOL`, `INT64`, `FLOAT64`, `NUMERIC`, or `BIGNUMERIC`. `DATE`, `TIMESTAMP`, `BYTES`, `JSON`, `GEOGRAPHY`, `ARRAY`, and `STRUCT` are rejected -- `EXTRACT` date parts into integers first.

**Task selection is implicit and type-driven.** There is no `task_type` argument:

| Label column type | Task | Added output columns |
|---|---|---|
| `INT64`, `FLOAT64`, `NUMERIC`, `BIGNUMERIC` | Regression | `predicted_<label>` (same type as the label) |
| `BOOL`, `STRING` | Classification | `predicted_<label>`, plus `predicted_<label>_probs` as `ARRAY<STRUCT<label STRING, prob FLOAT64>>` |

> **Cast your label.** A categorical encoded as INT64 (0/1, or a 1–5 rating) is silently treated as *regression* and you get fractional predictions with no probabilities. Cast it to `STRING` or `BOOL` to get classification. This consequence follows from the documented rule but is not itself documented.

The `label` subfield of `predicted_<label>_probs` is typed `STRING` even when the label column is `BOOL`. Array element ordering is not documented.

**Outputs:** The prediction input's columns plus the predicted column(s) above.

> **Doc bug.** The reference page states that AI.PREDICT "returns the columns from the training table or query result". Both of Google's own worked examples contradict this -- the returned rows are the *prediction* rows. Trust the behavior, not the sentence.

**Supported models:** TabFM only. Not selectable -- there is no `model` argument and no version pinning.

**Best practices:** Keep the feature set tight; the 50-column cap is a hard limit, not a guideline. Split train/predict deterministically (e.g. `FARM_FINGERPRINT`) so that the same rows train and predict on every run -- note this pins the *split* only; the predictions themselves are not reproducible (see Limitations). Pair every AI.PREDICT call with `AI.EVALUATE` on a held-out set -- without a metric you have no idea whether the zero-shot prediction is any good. Use it as a baseline: if a trained `CREATE MODEL` beats it materially, the training cost is justified; if not, you have saved a model lifecycle.

**Limitations:**
- **Output is not deterministic.** Repeating a byte-identical `AI.PREDICT` call over the same `FARM_FINGERPRINT` split returns slightly different predictions -- consistent with the model averaging shuffled ensemble passes (`n_ensembles`, whose value Google does not document). Demonstrated by `functions/ai_predict/ai_predict.ipynb` cells 25 and 28, whose top-5 multisets differ (`5760` vs `5728` in one slot) despite identical SQL and an `ORDER BY value DESC LIMIT 5`, so tie-breaking cannot explain it. The `workflows/tabular_prediction/` notebook shows the downstream consequence: `AI.EVALUATE` scores its *own* fresh TabFM predictions rather than the rows you materialized, so the two disagree (measured across four runs: regression MAE 236.52 / 236.35 / 235.84, classification accuracy 0.9468 / 0.9362 / 0.9468 -- regression drift well under 1%, classification drift about 1pp, or 2 rows in 94). **Materialize results once and join to them; do not re-run the prediction to reproduce a number.** Drift appears to be input-dependent -- `workflows/data_enrichment/` reproduced exactly across two runs on a 6-row prediction relation -- so absence of drift on a small input is not evidence of determinism.
- **50 feature columns** maximum (documented; was 20 until October 2026 — measured 2026-10-12: 50 runs, 51 fails with *The number of features 51 exceeds the maximum allowed number of features 50*). Escalation path is emailing bqml-feedback@google.com.
- **10 classification categories** maximum (documented).
- **Practical row ceiling, undocumented but observed:** a call with 10,000 training rows fails with `Resources exceeded ... allotted memory`; 8,000 rows succeeds. Budget for roughly 5,000 training rows on on-demand slots. Re-checked 2026-09-15: the two caps above are on **columns and classes**, not rows — the page still documents no row limit, so this remains an observation of ours rather than a published figure.
- **Latency is flat and high:** 30--95 seconds per call regardless of input size. A notebook with several AI.PREDICT calls takes minutes, not seconds.
- Max prediction rows, max input size, timeouts, concurrency, NULL handling, categorical encoding, and the `n_ensembles` value are all **undocumented**. AI.PREDICT does not appear in any table on the BigQuery quotas page.
- Whether these limits also bind `AI.EVALUATE`'s TabFM branch is undocumented, though it runs the same model.

**Locations:** Not stated on the AI.PREDICT page. The AI.EVALUATE page says TabFM is available in all supported BigQuery ML locations (non-remote models), plus the US and EU multi-regions.

**Pricing:** Today, standard BigQuery slot / bytes-processed pricing. **From 2026-10-30**, TabFM moves to token-based pricing: you are charged for TabFM tokens plus slots/bytes for the non-inference parts of the query.

```
Input tokens  = (train_rows * columns + predict_rows * (columns - 1)) * n_ensembles
Output tokens = predict_rows * n_ensembles
```

at $0.05 / mtok input and $0.20 / mtok output (re-read on the pricing page 2026-10-12; formula and rates unchanged). Note that `n_ensembles` -- the number of shuffled passes the model averages -- is a multiplier on your bill that Google does not document the value of.

> **A `COUNT(*)` over `AI.PREDICT` does not run the model.** Measured 2026-10-12: `SELECT COUNT(*) FROM AI.PREDICT(...)` returned in under 2 seconds with the right row count, while the same call selecting `predicted_<label>` took the usual 45-50 seconds -- the planner prunes the inference when no predicted column is referenced. Two consequences: a row-count smoke test proves nothing about whether the call *works* (the 10-class cap, for one, is only enforced once inference runs), and a probe that references a predicted column is what you need to see an error or pay for a prediction.

**Provisioned throughput:** Not specified.

**BigFrames API:** No wrapper. `bigframes.bigquery.ai` has `forecast` but no `predict` -- checked against **bigframes 2.39.0**, this project's pin in `uv.lock` and the version that executed `functions/ai_predict/ai_predict.ipynb`. Use `%%bigquery` magics or `session.read_gbq_query()`.

---
