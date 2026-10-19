# Model Introspection: `ML.FEATURE_INFO`, `ML.TRAINING_INFO`, `ML.TRIAL_INFO`

> **Source:** [`bigquery-ml/reference/model-lifecycle-functions.md#model-introspection-mlfeature_info-mltraining_info-mltrial_info`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ml/reference/model-lifecycle-functions.md#model-introspection-mlfeature_info-mltraining_info-mltrial_info)

These three table-valued functions read metadata that BigQuery ML records *during training*. They take no input data — they describe the model itself: the features it saw, how training converged, and (for tuned models) what each hyperparameter trial did. All three are GA.

---
