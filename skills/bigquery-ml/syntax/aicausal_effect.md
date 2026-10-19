# `AI.CAUSAL_EFFECT`

> **Source:** [`bigquery-ml/reference/model-free-functions.md#aicausal_effect`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ml/reference/model-free-functions.md#aicausal_effect)

> **Why an `AI.*` function is documented here.** The dividing line between this project and [`bigquery-ai`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ai/RESOURCES.md) is *"does the reader manage a model artifact,"* not *"does the name start with `AI.`"* — and by that test this function belongs with the model-free `ML.*` TVFs above. It creates nothing, and its subject is causal inference, the topic [`workflows/`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ml/README.md#workflows) already covers in five other places. The sibling project keeps a pointer so its `AI.*` list stays complete.

- **Description:** Table-valued function implementing [CausalImpact](https://google.github.io/CausalImpact/)-style intervention analysis (Brodersen et al., 2015). Given **one series and one intervention timestamp**, it fits a counterfactual on the pre-intervention window and reports the cumulative gap afterward, with a p-value. Two substitutions against the original method, both measured here: `ARIMA_PLUS` stands in for the Bayesian structural time series model, and a closed form stands in for its posterior sampling. It accepts **no control series and no covariates** — the documentation's stated reason is avoiding bias from experiment spillover effects.
- **Use cases:**
  - Estimating the effect of a launch, price change, outage or policy when no control group exists and no experiment was run.
  - Screening many series at once via `id_cols` — each unit is analyzed independently and returns its own row.
  - A first pass before reaching for [`difference_in_differences`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ml/workflows/difference_in_differences) or [`synthetic_control`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ml/workflows/synthetic_control), which are stronger but need a control unit.
- **documentation:** [AI.CAUSAL_EFFECT](https://docs.cloud.google.com/bigquery/docs/reference/standard-sql/bigqueryml-syntax-causal-effect)
- **Type:** Table-valued (TVF).
- **Applies to models:** None — model-free. Verified: model count in the dataset identical before and after, and `INFORMATION_SCHEMA.JOBS` shows a single `SELECT` job with `parent_job_id` null and no child jobs.
- **Status:** **Preview** as of 2026-09-16. **Connection required:** No.

**Syntax:**
```sql
AI.CAUSAL_EFFECT(TABLE, timestamp_col => STRING, data_col => STRING,
                 intervention_timestamp => TIMESTAMP literal,
                 [id_cols => ARRAY<STRING>], [num_post_intervention_points => INT64],
                 [confidence_level => FLOAT64], [output_time_series => BOOL])
```

**Inputs:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| (first argument) | relation | Yes | — | A `TABLE` reference or parenthesized subquery. |
| `timestamp_col` | `STRING` | Yes | — | Name of the `TIMESTAMP` column. |
| `data_col` | `STRING` | Yes | — | Name of the metric column. |
| `intervention_timestamp` | `TIMESTAMP` **literal** | Yes | — | Splits pre from post. Must be a literal — see limitations. |
| `id_cols` | `ARRAY<STRING>` | No | — | `STRING`/`INT64` columns identifying separate series; each combination returns its own row. |
| `num_post_intervention_points` | `INT64` | No | all | Caps how many post-intervention points are included. |
| `confidence_level` | `FLOAT64` in `[0, 1)` | No | `0.95` | Sets the pointwise `lower_bound`/`upper_bound` only — **not** `p_value`. |
| `output_time_series` | `BOOL` | No | `FALSE` | `TRUE` adds the pointwise columns. |

**Outputs:**

| Mode | Columns |
|---|---|
| Default | `absolute_effect`, `relative_effect`, `p_value`, `prob_causal_effect`, `status` |
| `output_time_series => TRUE` | the above repeated on every row, plus `<timestamp_col>`, `is_post_intervention`, `<data_col>`, `predicted_<data_col>`, `lower_bound`, `upper_bound` |

`absolute_effect` is the **cumulative** gap over the post-intervention window, not a per-period rate. `prob_causal_effect` is exactly `1 - p_value`. Pre-intervention rows carry `NULL` for the predicted and bound columns. `lower_bound`/`upper_bound` bound the **counterfactual at each timestamp** — there is no interval on the cumulative effect in either mode.

**Measured behavior** (Texas weekly COVID case rate per 100k, 9 pre-intervention weeks and 5 post, verified 2026-09-16):

| Component | Finding |
|---|---|
| Counterfactual | **Bit-for-bit identical** to `ARIMA_PLUS` + `ML.FORECAST` on default options — all 5 forecasts and all 10 interval bounds compare equal under exact float equality. |
| `absolute_effect` | `SUM(actual - expected)` over the post rows. Reproduced by hand exactly. |
| `relative_effect` | `SUM(actual - expected) / SUM(expected)`. Reproduced by hand exactly. |
| `p_value` | **Reproduces exactly**, as `2 · (1 − CDF(\|Z\|))` with `Z = absolute_effect ÷ Σ standard_error` and the `CDF` being the A&S 26.2.18 approximation below. Reported `0.304812168`; reconstructed `0.304812168`, equal bit for bit, and equal at all three post-window lengths swept. Both ingredients are unusual. The variance is the **sum** of the pointwise standard errors — the perfect-positive-correlation *ceiling* of the family, not a member of it, hence deliberately conservative: the widest interval and largest p-value any correlation structure among these errors can justify. The statistically correct construction, the ψ-weight cumulation at `266.695866`, would give `0.289301`. The tail area is then evaluated with the approximation rather than the exact normal, which the exact normal would put at `0.304354877`. Sizes: the conservative variance choice is worth `0.015054` of p-value, the approximation `0.000457` — 33× smaller. |
| Interval multiplier | `ML.FORECAST`'s bounds are **not** `forecast ± Φ⁻¹((1+cl)/2) · standard_error`. At `confidence_level => 0.95` the multiplier is `1.9564581` against a normal quantile of `1.9599640` — 0.18% narrow. Across five levels it is the inverse of **Abramowitz & Stegun 26.2.18** (the Hastings quartic, `\|error\| < 2.5e-4`) to about a millionth, while the exact normal misses by up to `0.0119` with a sign that changes. Full table in [`model-lifecycle-functions.md`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ml/reference/model-lifecycle-functions.md#mlforecast). Use the `standard_error` column; do not back it out of the bounds. |
| Determinism | Deterministic. Identical to the last digit across cache-disabled repeat calls, unlike the TimesFM-backed `AI.*` functions. |
| `confidence_level` | `p_value` is **invariant** to it while the interval widths move, so the p-value derives from the model's internal variance rather than the rendered bounds. |
| Engine | Fixed. `model => 'TimesFM 2.0'` fails with *"Named argument model not found in signature."* Despite the `AI.` prefix, it shares no engine with `AI.FORECAST`. |

**Best practices:**
- Divide `absolute_effect` by the number of post-intervention points before comparing against any per-period estimate.
- **Rebuild the counterfactual as an `ARIMA_PLUS` model when the answer matters.** Because the function returns no artifact, there is otherwise no `ML.ARIMA_EVALUATE` to tell you the selected order and no `ML.EXPLAIN_FORECAST` to show the decomposition. On the tested series `auto_arima` chose `(0, 2, 0)` with `has_drift = False` and `[NO_SEASONALITY]` — a twice-differenced random walk, which is exactly why the counterfactual is a perfect straight line.
- Read the p-value before quoting the point estimate. On a short pre-period the two often disagree about what the data supports.
- **Build the interval the function does not return.** `absolute_effect ± q · Σ standard_error`, with `q` the inverse of the same approximation, gives a range on the cumulative effect that agrees with the reported p-value by construction (it straddles zero exactly when `p > 1 − confidence_level`). On the tested series: `[−820.90, +255.69]` at 0.95 against a point estimate of `−282.61`. Report that alongside the threshold verdict — a range spanning a large reduction, no change, and a moderate increase says far more than "`p > 0.05`". Use the ceiling variance, not the ψ cumulation, or the interval will quietly contradict the p-value beside it.
- Test `status` with `status = ''`; it is the empty string on success.

**Limitations:**
- **`intervention_timestamp` must be a literal.** `TIMESTAMP '2020-07-03'` works; `TIMESTAMP("2020-07-03")` fails with *"expects the intervention_timestamp argument to be a TIMESTAMP literal, but TIMESTAMP was provided."* It cannot be a query parameter or a computed expression, so parameterizing the call means string-substituting the SQL.
- **No `ARIMA_PLUS` options are reachable** — no `holiday_region`, `data_frequency`, or manual `(p,d,q)`. Defaults or nothing.
- **A univariate counterfactual cannot see a common shock.** It attributes the *entire* deviation from the unit's own past trend to the intervention. Measured on one dataset against two control-based estimators: `AI.CAUSAL_EFFECT` **−56.52** per week versus difference-in-differences **−19.29** and synthetic control **−19.28** — same sign, ~2.9× the magnitude, because the control methods net out a nationwide surge the donor states also experienced and this function has no way to. There is no diagnostic inside the function that flags this. The trade runs both ways, though: a control unit removes the common shock but imports whatever else is in the control, and if the control is itself touched by the intervention the spillover biases the estimate toward zero. Which bias you would rather carry is the actual choice.
- **Three points is a hard floor, not a sensible minimum.** Below three, `status` returns *"The time series data is too short."* Nine pre-period points already produced a counterfactual with no seasonal structure and week-5 intervals of ±200 on a series whose full observed range is ~203.
- **No interval is returned on the effect.** `lower_bound` and `upper_bound` bound the *counterfactual* at each timestamp, not the cumulative gap, so the summary row offers a threshold verdict and no range. See the best practice above for building one.
- **No model artifact is produced.** The counterfactual is fitted and discarded: nothing to inspect, re-use, grant access to, or apply to later data, and no `ML.EXPLAIN_FORECAST` to point at. Rebuilding it as `ARIMA_PLUS` is the only way to get one.
- Prediction intervals are exactly symmetric around the forecast and widen quickly with horizon.
- **`id_cols` fans out rather than pooling.** Each series is analysed independently — results are bit-identical to separate single-series calls (largest disagreement across nine values: exactly 0.0) — so there is no shared trend, no pooled variance, and **no multiple-comparison adjustment** on the p-values it returns.
- **`relative_effect` is not unit-free.** It is invariant to scaling and to negation, but a constant *shift* moves it (−0.2205 → −0.1586 on adding 100 to every point) because the shift inflates the `SUM(expected)` denominator. It is only interpretable on a ratio scale with a meaningful zero.
- **Preview** — arguments and output columns can change.

**Related:** [`AI.KEY_DRIVERS`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ai/reference/augmented-analytics.md) is the other augmented-analytics `AI.*` function Google groups with this one; it answers "which dimensions explain a metric change," not "did this intervention cause one." For the control-based alternatives see [`workflows/difference_in_differences/`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ml/workflows/difference_in_differences) and [`workflows/synthetic_control/`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ml/workflows/synthetic_control).

**BigFrames API:** No equivalent — `bigframes.bigquery` exposes several `AI.*` functions but not this one. Reach it via `bigframes.pandas.read_gbq` over the SQL. `bigframes.ml.forecasting.ARIMAPlus` does cover the manual-reproduction path.

**Repo example (tested):** `bigquery-ml/workflows/causal_effect/causal_effect.ipynb` and `causal_effect.sql` — the bit-for-bit `ARIMA_PLUS` reproduction, the effect-formula invariance battery (scale, shift, negation), the seven p-value constructions plus the exact reconstruction and the post-window sweep, the interval-multiplier identification, the constructed effect interval, the `confidence_level` and determinism probes, the `id_cols` fan-out check, and the three-estimator comparison on one panel.

---
