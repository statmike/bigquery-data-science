# Model monitoring & data validation

> **Source:** [`bigquery-ml/reference/model-management-monitoring.md#model-monitoring--data-validation`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ml/reference/model-management-monitoring.md#model-monitoring--data-validation)

BigQuery ML ships four built-in functions for **training/serving skew** and **data drift** monitoring.
They are model-light: skew uses statistics saved at training time
(no original training data needed); drift compares two arbitrary datasets. None require a Cloud resource
connection. The optional `MODEL` argument only enables a Vertex AI **visualization link** and requires the
model to be registered in Vertex AI Model Registry. Two tiers exist:

- **Basic** (`ML.VALIDATE_DATA_SKEW`, `ML.VALIDATE_DATA_DRIFT`) — tabular output, anomaly flags.
- **Advanced / TFDV-compatible** (`ML.TFDV_DESCRIBE`, `ML.TFDV_VALIDATE`) — emit/consume a TensorFlow
  `DatasetFeatureStatisticsList` proto as JSON, for use with the `tensorflow-data-validation` library.

Status: **GA**. See the [Model monitoring overview](https://cloud.google.com/bigquery/docs/model-monitoring-overview).

> Cross-reference: `ML.DETECT_ANOMALIES` (anomaly detection from a trained model) and `AI.DETECT_ANOMALIES`
> (foundation-model time-series anomalies) are distinct — see the model-type entries / `../bigquery-ai/`.

> **Profiling moved.** `ML.DESCRIBE_DATA` used to be listed here as a fifth, Basic-tier function. It answers a
> different question — *what is in this dataset*, not *has this dataset changed* — so its entry now lives with
> `ML.CORRELATION` under [Model-Free Functions → Exploratory data analysis](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ml/reference/model-free-functions.md#exploratory-data-analysis-mldescribe_data-mlcorrelation),
> demonstrated in [`functions/exploration/`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ml/functions/exploration). Profile there, monitor here.
