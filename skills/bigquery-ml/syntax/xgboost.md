# `XGBOOST`

> **Source:** [`bigquery-ml/reference/create-model-model-types.md#xgboost`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ml/reference/create-model-model-types.md#xgboost)

- **Description:** Imports an XGBoost Booster model (`.bst` or `.json`) for inference.
- **When to use:**
  - You trained XGBoost outside BigQuery and want SQL serving plus tree feature importance.
  - You need an explicit input/output schema mapping (`INPUT(...) OUTPUT(...)`).
- **Category:** imported. **Connection required:** No (object-table serving needs reservations). **Status:** GA.
- **documentation:** [CREATE MODEL (XGBoost)](https://cloud.google.com/bigquery/docs/reference/standard-sql/bigqueryml-syntax-create-xgboost)

**CREATE MODEL syntax:**
```sql
CREATE OR REPLACE MODEL `PROJECT_ID.DATASET.MODEL_NAME`
INPUT(f1 INT64, f2 FLOAT64, f3 FLOAT64)
OUTPUT(predicted_label FLOAT64)
OPTIONS(
  MODEL_TYPE = 'XGBOOST',
  MODEL_PATH = 'gs://bucket/path/to/xgboost_model/*'
);
```

**Options & clauses:**

| Option / Clause | Type | Required | Description |
|---|---|---|---|
| `MODEL_TYPE` | STRING | Yes | `'XGBOOST'`. |
| `MODEL_PATH` | STRING | Yes | GCS URI of the Booster file. Use a `.json` or `.ubj` extension — a `.bst` upload is rejected regardless of contents (see the gotcha below). |
| `KMS_KEY_NAME` | STRING | No | CMEK to encrypt the model. |
| `INPUT(field_name field_type, …)` | clause | Conditional | Input schema. **Optional only if** `feature_names` AND `feature_types` are both stored in the model file (see XGBoost Model IO / JSON Schema). Input types must be supported numeric types; names must match `feature_names`. |
| `OUTPUT(field_name field_type, …)` | clause | Conditional | Output schema. Output type must be `FLOAT64`. |

**Supported lifecycle functions:** `ML.PREDICT` and **`ML.FEATURE_IMPORTANCE`** (the only imported type
that supports a feature-attribution function).
**Limitations:** Booster format only, uploaded as `.json` or `.ubj`; model must exist in GCS before import.
**250 MB** size limit; **840 MB** memory limit to load+run (reduce trees / depth, or save via XGBoost's
default `save_model` to shrink). Object-table use is reservation-only.

**GOTCHA (verified live, undocumented as of this writing):** what the importer accepts is decided by
the artifact's **file extension**, not by the library version that wrote it. Measured by saving one
Booster from `xgboost` 3.3.0 three ways and importing each:

| Uploaded as | Result |
|---|---|
| `model.json` | Imports; `ML.PREDICT` and `ML.FEATURE_IMPORTANCE` both work |
| `model.ubj` | Imports |
| `model.bst` | Rejected — `Invalid XGBoost model: could not load model from file`, a JSON parse error at character position 1 |

The `.bst` and `.ubj` uploads were **byte-identical** in that test (current xgboost writes UBJSON under
either extension), so the difference is the name, not the contents. **Save as `.json` or `.ubj` and no
version pin is needed.** This retires an earlier reading of this behavior as a blanket "Booster must
come from XGBoost ≤ 1.5.1" cap — a modern booster imports fine under the right extension.

Note the matching quirk in the other direction: `EXPORT MODEL` writes `model.bst` at the
`xgboost_version = '0.9'` default and `model.ubj` at `'2.1'` — so a BQML-exported tree ensemble is
re-importable as-is only when it was trained at `2.1`.

**BigFrames API:** `bigframes.ml.imported.XGBoostModel(model_path=..., input=..., output=...)`.
**Repo example (tested):** `bigquery-ml/models/imported/imported.ipynb`
(Step 3) — a binary classifier (`objective='binary:logistic'`) trained natively with `xgboost.train()`
on an unpinned current `xgboost`, saved as `.json`, imported with explicit `INPUT`/`OUTPUT` (a `multi:softprob`
objective also predicts fine but silently returns an ARRAY despite a scalar `OUTPUT` declaration — a
binary objective keeps the declared type honest). `ML.FEATURE_IMPORTANCE` verified working here.

---

**Connection matrix note:** Imported models occupy the "imported" column of the connection matrix —
**no connection** for standard `ML.PREDICT` on the GCS-loaded model; a Cloud Resource connection +
reservation pricing only when serving against an object table.


---
