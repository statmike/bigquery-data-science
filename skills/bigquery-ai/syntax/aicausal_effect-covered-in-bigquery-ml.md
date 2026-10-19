# `AI.CAUSAL_EFFECT` — covered in `bigquery-ml`

> **Source:** [`bigquery-ai/reference/augmented-analytics.md#aicausal_effect--covered-in-bigquery-ml`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ai/reference/augmented-analytics.md#aicausal_effect--covered-in-bigquery-ml)

Full entry: **[`bigquery-ml/reference/model-free-functions.md#aicausal_effect`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ml/reference/model-free-functions.md#aicausal_effect)**
Tested example: **[`bigquery-ml/workflows/causal_effect/`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ml/workflows/causal_effect)**

This is a deliberate exception to the usual rule that every `AI.*` function is documented in this project. The dividing line between the two projects is *"does the reader manage a model artifact,"* not *"does the name start with `AI.`"* — and by that test this one belongs there:

- Its subject is **causal inference**, which `bigquery-ml/workflows/` already covers five other ways ([DiD](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ml/workflows/difference_in_differences), [synthetic control](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ml/workflows/synthetic_control), [propensity score matching](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ml/workflows/propensity_score_matching), [uplift/CATE](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ml/workflows/uplift_cate), [double ML](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ml/workflows/price_elasticity_dml)). The only way to judge its estimate is against those, on the same data — which is exactly what the linked notebook does, and it finds a ~2.9× magnitude disagreement.
- It is **not foundation-model backed**. Unlike every other function in this project, its counterfactual is measurably plain `ARIMA_PLUS` + `ML.FORECAST` on default options — identical to the last digit — and it rejects the `model` argument the TimesFM functions accept. It is also fully deterministic, which none of the TimesFM functions are: its p-value is a closed form, `2 · (1 − CDF(\|Z\|))` on the sum of the model's own pointwise standard errors, reconstructible bit for bit rather than sampled.

It stays listed in this project's [function catalog](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ai/README.md#augmented-analytics--find-what-drives-metric-changes) so that catalog remains a complete inventory of the `AI.*` surface.

**Where it appears in this project anyway:** [`workflows/metric_diagnostics/`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ai/workflows/metric_diagnostics) runs it as a **placebo test** at the end of an `AI.KEY_DRIVERS` → `AI.PREDICT` diagnostic. There is no intervention in that dataset, which is the point: six dates chosen only for spacing, and one of them returns a significant cumulative effect with nothing behind it, because a counterfactual fitted on a spring-and-summer ramp reads the autumn seasonal turn as an intervention. That is the discipline the shared heading makes easy to skip — the same trap as reading `AI.KEY_DRIVERS` on before/after periods as causal, arriving from the other direction.

---
