# Exploratory data analysis: `ML.DESCRIBE_DATA`, `ML.CORRELATION`

> **Source:** [`bigquery-ml/reference/model-free-functions.md#exploratory-data-analysis-mldescribe_data-mlcorrelation`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ml/reference/model-free-functions.md#exploratory-data-analysis-mldescribe_data-mlcorrelation)

The two questions asked of a dataset before anything is modeled: *what is in it* and *what moves with the target*. Both are table-valued functions, both are model-free, and neither needs a connection.

They are deliberately **not** filed with the data-quality functions. `ML.VALIDATE_DATA_SKEW` / `ML.VALIDATE_DATA_DRIFT` answer "has this dataset **changed**" — a comparison between two relations. These two answer "what **is** this dataset" from one relation. Profile here, monitor in [Model Management & Monitoring](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ml/reference/model-management-monitoring.md#model-monitoring--data-validation).

**Repo example (tested):** [`functions/exploration/`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ml/functions/exploration) — `exploration.ipynb` and `exploration.sql` cover both functions end to end.

---
