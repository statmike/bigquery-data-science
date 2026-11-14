> **Source (`statmike/bigquery-data-science`):** **Notebook:** [`bigquery-ml/pipelines/bigquery_pipelines/bigquery_pipelines.ipynb`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ml/pipelines/bigquery_pipelines/bigquery_pipelines.ipynb)

# BigQuery Studio Pipelines — SQL Unit Tests, Mixed SQL + Notebook DAGs, Metadata Enrichment & Cron Scheduling

Operationalizes `workflows/ga4_churn_prediction` (`workflows/ga4_churn_prediction/`) using **BigQuery Studio Pipelines** (formerly called *"BigQuery Workflows"* in the Google Cloud Console) via its underlying `google.cloud.dataform_v1` API.

While `pipelines/dataform` (`pipelines/dataform/`) demonstrates the foundational `.sqlx` dependency graph and a deliberately failing `assertion` that halts downstream scoring, this companion notebook covers the **2026 BigQuery Studio Pipelines feature wave** on `dataformCoreVersion: 3.1.0`:
1. **SQL Unit Tests (`type: "test"`, GA `2026-09-17`)** — validates the GA4 feature-engineering logic against synthetic inline mock `input` rows (`0` bytes scanned) before touching production tables or training a model.
2. **Mixed SQL + Python Notebook DAG (`notebook({...})`)** — chains `.sqlx` views, tables, BQML `CREATE MODEL` operations, and assertions with a headless Colab Enterprise `.ipynb` notebook task in a single compiled dependency graph.
3. **Metadata Enrichment (GA `2026-10-01`) & Automatic Lineage (GA `2026-11-12`)** — propagates table descriptions, column descriptions, and `bigquery.labels` through `CompilationResult` with `CodeCompilationConfig(lineage_enabled=True)`, plus documents `preserveGovernanceControls` (GA `2026-10-20`) and action concurrency limits (GA `2026-11-09`).
4. **End-to-End Passing `WorkflowInvocation` & Scheduled `ReleaseConfig` + `WorkflowConfig`** — executes the full SQL + BQML pipeline to `SUCCEEDED` (materializing batch `ML.PREDICT` churn scores) and configures production Git-committed cron scheduling.

**Workflow operationalized:** `workflows/ga4_churn_prediction` (`workflows/ga4_churn_prediction/`)
**Sister notebook on the same API:** `pipelines/dataform` (`pipelines/dataform/`)
**API:** `google.cloud.dataform_v1` (`Repository`, `Workspace`, `CompilationResult`, `WorkflowInvocation`, `ReleaseConfig`, `WorkflowConfig`)

**Data:** [`bigquery-public-data.ga4_obfuscated_sample_ecommerce`](https://console.cloud.google.com/marketplace/product/bigquery-public-datasets)

**References:** `RESOURCES.md` (Full reference) | [BigQuery Pipelines overview](https://cloud.google.com/bigquery/docs/pipelines-introduction) | [Dataform SQL unit tests](https://cloud.google.com/dataform/docs/unit-testing) | [Schedule pipelines](https://cloud.google.com/bigquery/docs/scheduling-pipelines) | `setup` (Setup guide)

---
## Product Evolution & Comparison with `pipelines/dataform/`

Google originally launched **Dataform** (`dataform.googleapis.com`) for declarative `.sqlx` transformations and assertions. BigQuery Studio then introduced **BigQuery Workflows** on top of that same Dataform API so users could build visual DAGs combining SQL queries and Colab Enterprise notebooks directly inside BigQuery Studio. In 2026, Google **renamed "BigQuery Workflows" to "BigQuery Pipelines"** (avoiding confusion with Google Cloud Workflows, covered in `pipelines/cloud_workflows` (`pipelines/cloud_workflows/`)) and shipped SQL unit tests, notebook tasks, metadata enrichment, governance preservation, concurrency limits, and Knowledge Catalog lineage on the shared `dataform_v1` backend:

| Dimension | **`pipelines/dataform` (`pipelines/dataform/`)** (Classic `.sqlx` DAG) | **This Notebook (`pipelines/bigquery_pipelines/`)** |
| --- | --- | --- |
| **Control-Plane API** | `google.cloud.dataform_v1` | `google.cloud.dataform_v1` *(identical backend API)* |
| **Compiler Version (`workflow_settings.yaml`)** | `dataformCoreVersion: 3.0.0` | `dataformCoreVersion: 3.1.0` (required for `bigqueryUnitTest` & `notebook` actions) |
| **Pre-Execution SQL Unit Tests (`type: "test"`, GA `2026-09-17`)** | Not used | **Yes** — tests the GA4 feature-engineering logic on inline mock `input` rows (`0` bytes billed) via compiled `bigqueryUnitTest` (`testQuery` vs `expectedOutputQuery`) |
| **Metadata Enrichment (GA `2026-10-01`) & Lineage (GA `2026-11-12`)** | Default table creation | **Yes** — table/column `description`s, `bigquery.labels`, and `CodeCompilationConfig(lineage_enabled=True)` |
| **Mixed SQL + Python Notebook DAG (`notebook` action)** | `.sqlx` actions only (`table`, `operations`, `assertion`) | **Yes** — compiles a multi-language DAG chaining `.sqlx` feature/model/assertion/scoring nodes with a headless `.ipynb` Colab Enterprise notebook action (`notebook({...})`) |
| **Quality Gate & Execution Outcome** | Deliberately **fails** a strict assertion (`roc_auc < 0.99`) to prove downstream `scoring` is `SKIPPED` | Passes the `roc_auc >= 0.60` assertion so downstream `scoring` materializes **`SUCCEEDED`**, then commits to Git and provisions **`ReleaseConfig` + `WorkflowConfig`** |

---
## Setup

Set your project and location, authenticate, and create the shared `bq_ml` dataset.

```python
import os
from pathlib import Path
import google.auth

PROJECT_ID = 'your-gcp-project-id'  # <-- Replace with your project ID (or leave to auto-detect)
if PROJECT_ID == 'your-gcp-project-id':
    for _p in [Path.cwd(), *Path.cwd().parents]:
        if (_p / '.env').is_file():
            for _k, _v in (l.split('=', 1) for l in (_p / '.env').read_text().splitlines() if '=' in l and not l.strip().startswith('#')):
                os.environ.setdefault(_k.strip(), _v.strip().strip('\'"'))
            break
    PROJECT_ID = os.environ.get('GOOGLE_CLOUD_PROJECT') or google.auth.default()[1] or 'your-gcp-project-id'
LOCATION = 'US'  # BigQuery dataset location
DATASET_ID = 'bq_ml'  # Shared dataset across all bigquery-ml notebooks
DATAFORM_LOCATION = 'us-central1'  # Dataform / BigQuery Pipelines requires a regional control plane
```

### Environment

> **Already set up the project environment?** The cell below is a no-op — packages are already in your kernel. See the `setup` (Setup Reference) for details.
>
> **Running standalone** (Colab, Colab Enterprise, Vertex AI Workbench)? The cell below installs required packages into your current kernel.

```python
from google.cloud import bigquery
import pandas as pd

client = bigquery.Client(project=PROJECT_ID)
pd.set_option('display.max_colwidth', None)

# Create the shared dataset (idempotent)
dataset_ref = bigquery.DatasetReference(PROJECT_ID, DATASET_ID)
dataset = bigquery.Dataset(dataset_ref)
dataset.location = LOCATION
client.create_dataset(dataset, exists_ok=True)
print(f'Dataset {PROJECT_ID}.{DATASET_ID} ready')

# Register %%bigquery cell magic (auto-loaded in Colab, needed elsewhere)
%load_ext bigquery_magics
```

---
## Step 0 — Enable the Dataform API and verify service-agent IAM

BigQuery Studio Pipelines uses the Dataform API (`dataform.googleapis.com`) and requires the per-project Dataform service agent (`service-PROJECT_NUMBER@gcp-sa-dataform.iam.gserviceaccount.com`) to hold `roles/iam.serviceAccountTokenCreator` on the runtime service account that executes the pipeline's BigQuery jobs.

```python
import subprocess

def run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True)

# 1. Enable the Dataform API (idempotent)
result = run(['gcloud', 'services', 'enable', 'dataform.googleapis.com', '--project', PROJECT_ID])
if result.returncode == 0:
    print('Dataform API enabled (or already was)')
else:
    print('Could not enable Dataform API automatically:', result.stderr)

# 2. Determine the project number and the runtime service account
project_number = run(['gcloud', 'projects', 'describe', PROJECT_ID, '--format=value(projectNumber)']).stdout.strip()
runtime_service_account = f'{project_number}-compute@developer.gserviceaccount.com'
dataform_service_agent = f'serviceAccount:service-{project_number}@gcp-sa-dataform.iam.gserviceaccount.com'
print('Runtime service account configured')

# 3. Verify that the Dataform service agent has Token Creator on the runtime service account
policy = run(['gcloud', 'iam', 'service-accounts', 'get-iam-policy', runtime_service_account,
              '--project', PROJECT_ID, '--format=json'])
has_binding = dataform_service_agent in policy.stdout and 'serviceAccountTokenCreator' in policy.stdout

if has_binding:
    print('IAM binding already in place: Dataform can impersonate the runtime service account.')
else:
    print('Granting roles/iam.serviceAccountTokenCreator to the Dataform service agent...')
    grant = run(['gcloud', 'iam', 'service-accounts', 'add-iam-policy-binding', runtime_service_account,
                 f'--member={dataform_service_agent}',
                 '--role=roles/iam.serviceAccountTokenCreator',
                 '--project', PROJECT_ID])
    if grant.returncode == 0:
        print('Granted roles/iam.serviceAccountTokenCreator.')
    else:
        print('Could not grant automatically. Ask a project admin to grant roles/iam.serviceAccountTokenCreator.')
```

---
## Step 1 — Create the BigQuery Pipeline repository and workspace

We pass `service_account=runtime_service_account` on the `Repository` resource and use `transport='rest'` on `DataformClient` so any compilation or validation diagnostics return complete HTTP JSON payloads without hitting gRPC's 8 KB trailing-metadata limit.

```python
from google.cloud import dataform_v1

dataform_client = dataform_v1.DataformClient(transport='rest')
dataform_parent = dataform_client.common_location_path(PROJECT_ID, DATAFORM_LOCATION)
REPO_ID = 'bq-ml-ga4-churn-bq-pipeline'

repository = dataform_client.create_repository(
    parent=dataform_parent,
    repository_id=REPO_ID,
    repository=dataform_v1.Repository(service_account=runtime_service_account),
)
print('Repository:', repository.name)

workspace = dataform_client.create_workspace(
    parent=repository.name,
    workspace_id='dev',  # Must differ from the default branch name ('main')
    workspace=dataform_v1.Workspace(),
)
print('Workspace:', workspace.name)
```

---
## Step 2 — Write the BigQuery Studio Pipeline assets (`dataformCoreVersion: 3.1.0`)

Setting **`dataformCoreVersion: 3.1.0`** in `workflow_settings.yaml` unlocks two key 2026 BigQuery Studio Pipeline action types that fail to compile or silently drop in `3.0.0`:
1. **`type: "test"` SQL unit tests (`.sqlx`)** — compiled into `bigqueryUnitTest` actions (`testQuery` + `expectedOutputQuery`).
2. **`notebook({...})` tasks (`.js` + `.ipynb`)** — compiled into `CompilationResultAction.notebook` nodes.

### Verified live gotcha: wildcard table names (`events_*`) in `.sqlx` unit tests

Dataform's `.sqlx` `input "<name>"` lexer only accepts standard identifier characters (`[a-zA-Z0-9_-]+`). If a feature table references a wildcard declaration `${ref("events_*")}` directly, writing `input "events_*"` in a `.sqlx` unit test fails compilation with:
> `Input for dataset "{"name":"events_*"}" has not been provided.`

**The clean pattern:** wrap the wildcard source in a thin flattening view (`ga4_churn_bp_raw_events`, `type: "view"`). Downstream tables reference `${ref("ga4_churn_bp_raw_events")}`, and `.sqlx` unit tests mock `input "ga4_churn_bp_raw_events"` with clean, flat scalar columns (no nested `UNNEST(event_params)` mock boilerplate required).

We write 10 files into the workspace:
- `workflow_settings.yaml` (`dataformCoreVersion: 3.1.0`)
- `definitions/ga4_churn_bp_raw_events.sqlx` (`type: "view"` flattening `events_*`)
- `definitions/ga4_churn_bp_features.sqlx` (`type: "table"` with **metadata enrichment**: table `description`, per-column `columns` descriptions, and `bigquery.labels`)
- `definitions/test_features_pass.sqlx` (`type: "test"` — verifies that a user returning on day 14 is labeled `churned = FALSE` and a user with no activity in days 7–36 is labeled `churned = TRUE`)
- `definitions/test_features_fail.sqlx` (`type: "test"` — deliberately asserts the wrong `churned` label to demonstrate how a unit-test failure surfaces before any production table scan)
- `definitions/ga4_churn_bp_model.sqlx` (`type: "operations", hasOutput: true` — trains `BOOSTED_TREE_CLASSIFIER`)
- `definitions/ga4_churn_bp_quality_gate.sqlx` (`type: "assertion"` — requires `roc_auc >= 0.60`)
- `definitions/ga4_churn_bp_scoring.sqlx` (`type: "table", dependOnDependencyAssertions: true` — materializes batch `ML.PREDICT` churn scores with metadata descriptions)
- `definitions/ga4_churn_bp_report.ipynb` + `definitions/ga4_churn_bp_report.js` (`notebook({...})` action depending on `ga4_churn_bp_scoring`)

```python
import json

workflow_settings = f"""defaultProject: {PROJECT_ID}
defaultDataset: {DATASET_ID}
defaultLocation: {LOCATION}
defaultAssertionDataset: {DATASET_ID}_assertions
dataformCoreVersion: 3.1.0
"""

raw_events_sqlx = """config {
  type: "view",
  description: "Flattened GA4 event stream over the public events_* wildcard table"
}

SELECT
  user_pseudo_id,
  PARSE_DATE('%Y%m%d', event_date) AS event_date,
  event_name,
  device.category AS device_category,
  geo.country AS country,
  traffic_source.medium AS traffic_medium,
  (SELECT value.int_value FROM UNNEST(event_params) WHERE key = 'engagement_time_msec') AS engagement_time_msec
FROM `bigquery-public-data.ga4_obfuscated_sample_ecommerce.events_*`
"""

features_sqlx = """config {
  type: "table",
  description: "GA4 first-week behavioral features and 30-day churn label (BigQuery Studio Pipeline)",
  columns: {
    user_pseudo_id: "Pseudonymous GA4 user identifier",
    first_date: "Date of first observed visit in cohort window",
    n_events: "Total events recorded during the 7-day feature window",
    did_purchase: "Whether the user completed a purchase in the first 7 days",
    churned: "TRUE when user had zero events in days 7 to 36 after first_date"
  },
  bigquery: {
    labels: {
      orchestrator: "bigquery_pipelines",
      workflow: "ga4_churn_prediction"
    }
  }
}

WITH events AS (
  SELECT * FROM ${ref("ga4_churn_bp_raw_events")}
),
first_visit AS (
  SELECT user_pseudo_id, MIN(event_date) AS first_date
  FROM events
  GROUP BY user_pseudo_id
  HAVING first_date BETWEEN '2020-11-01' AND '2020-12-24'
),
feature_window AS (
  SELECT e.*, f.first_date
  FROM events e
  JOIN first_visit f USING (user_pseudo_id)
  WHERE e.event_date BETWEEN f.first_date AND DATE_ADD(f.first_date, INTERVAL 6 DAY)
),
label_window AS (
  SELECT DISTINCT e.user_pseudo_id
  FROM events e
  JOIN first_visit f USING (user_pseudo_id)
  WHERE e.event_date BETWEEN DATE_ADD(f.first_date, INTERVAL 7 DAY) AND DATE_ADD(f.first_date, INTERVAL 36 DAY)
)
SELECT
  fw.user_pseudo_id,
  ANY_VALUE(fw.first_date) AS first_date,
  ANY_VALUE(fw.device_category) AS device_category,
  ANY_VALUE(fw.country) AS country,
  ANY_VALUE(fw.traffic_medium) AS traffic_medium,
  COUNT(*) AS n_events,
  COUNT(DISTINCT fw.event_date) AS n_active_days,
  COUNTIF(fw.event_name = 'page_view') AS n_page_view,
  COUNTIF(fw.event_name = 'view_item') AS n_view_item,
  COUNTIF(fw.event_name = 'add_to_cart') AS n_add_to_cart,
  COUNTIF(fw.event_name = 'begin_checkout') AS n_begin_checkout,
  COUNTIF(fw.event_name = 'session_start') AS n_sessions,
  COUNTIF(fw.event_name = 'purchase') > 0 AS did_purchase,
  IFNULL(SUM(fw.engagement_time_msec), 0) AS total_engagement_time_msec,
  lw.user_pseudo_id IS NULL AS churned
FROM feature_window fw
LEFT JOIN label_window lw USING (user_pseudo_id)
GROUP BY fw.user_pseudo_id, lw.user_pseudo_id
"""

test_features_pass_sqlx = """config {
  type: "test",
  dataset: "ga4_churn_bp_features"
}

input "ga4_churn_bp_raw_events" {
  SELECT 'u_retained' AS user_pseudo_id, DATE '2020-11-01' AS event_date, 'purchase' AS event_name, 'desktop' AS device_category, 'US' AS country, 'organic' AS traffic_medium, 5000 AS engagement_time_msec
  UNION ALL
  SELECT 'u_retained' AS user_pseudo_id, DATE '2020-11-15' AS event_date, 'page_view' AS event_name, 'desktop' AS device_category, 'US' AS country, 'organic' AS traffic_medium, 1000 AS engagement_time_msec
  UNION ALL
  SELECT 'u_churned' AS user_pseudo_id, DATE '2020-11-02' AS event_date, 'page_view' AS event_name, 'mobile' AS device_category, 'CA' AS country, 'cpc' AS traffic_medium, 1200 AS engagement_time_msec
}

SELECT 'u_retained' AS user_pseudo_id, DATE '2020-11-01' AS first_date, 'desktop' AS device_category, 'US' AS country, 'organic' AS traffic_medium, 1 AS n_events, 1 AS n_active_days, 0 AS n_page_view, 0 AS n_view_item, 0 AS n_add_to_cart, 0 AS n_begin_checkout, 0 AS n_sessions, TRUE AS did_purchase, 5000 AS total_engagement_time_msec, FALSE AS churned
UNION ALL
SELECT 'u_churned' AS user_pseudo_id, DATE '2020-11-02' AS first_date, 'mobile' AS device_category, 'CA' AS country, 'cpc' AS traffic_medium, 1 AS n_events, 1 AS n_active_days, 1 AS n_page_view, 0 AS n_view_item, 0 AS n_add_to_cart, 0 AS n_begin_checkout, 0 AS n_sessions, FALSE AS did_purchase, 1200 AS total_engagement_time_msec, TRUE AS churned
"""

test_features_fail_sqlx = """config {
  type: "test",
  dataset: "ga4_churn_bp_features"
}

input "ga4_churn_bp_raw_events" {
  SELECT 'u_churned' AS user_pseudo_id, DATE '2020-11-02' AS event_date, 'page_view' AS event_name, 'mobile' AS device_category, 'CA' AS country, 'cpc' AS traffic_medium, 1200 AS engagement_time_msec
}

-- Deliberately wrong expectation: claims churned = FALSE for a user with zero events in days 7-36
SELECT 'u_churned' AS user_pseudo_id, DATE '2020-11-02' AS first_date, 'mobile' AS device_category, 'CA' AS country, 'cpc' AS traffic_medium, 1 AS n_events, 1 AS n_active_days, 1 AS n_page_view, 0 AS n_view_item, 0 AS n_add_to_cart, 0 AS n_begin_checkout, 0 AS n_sessions, FALSE AS did_purchase, 1200 AS total_engagement_time_msec, FALSE AS churned
"""

model_sqlx = """config { type: "operations", hasOutput: true }

CREATE OR REPLACE MODEL ${self()}
OPTIONS(
  model_type = 'BOOSTED_TREE_CLASSIFIER',
  input_label_cols = ['churned'],
  auto_class_weights = TRUE,
  data_split_method = 'AUTO_SPLIT',
  enable_global_explain = TRUE
) AS
SELECT n_events, n_active_days, n_page_view, n_view_item, n_add_to_cart,
       n_begin_checkout, n_sessions, did_purchase, device_category, country,
       traffic_medium, total_engagement_time_msec, churned
FROM ${ref("ga4_churn_bp_features")}
WHERE first_date <= '2020-11-20'
"""

quality_gate_sqlx = """config { type: "assertion" }

SELECT * FROM ML.EVALUATE(MODEL ${ref("ga4_churn_bp_model")})
WHERE roc_auc < 0.60
"""

scoring_sqlx = """config {
  type: "table",
  dependOnDependencyAssertions: true,
  description: "Batch churn predictions gated by ML.EVALUATE roc_auc >= 0.60 assertion",
  columns: {
    user_pseudo_id: "Pseudonymous GA4 user identifier",
    predicted_churned: "Predicted 30-day churn label from BOOSTED_TREE_CLASSIFIER"
  },
  bigquery: {
    labels: {
      orchestrator: "bigquery_pipelines",
      stage: "batch_scoring"
    }
  }
}

SELECT
  user_pseudo_id,
  predicted_churned,
  predicted_churned_probs
FROM ML.PREDICT(
  MODEL ${ref("ga4_churn_bp_model")},
  (SELECT * FROM ${ref("ga4_churn_bp_features")} WHERE first_date <= '2020-11-20' LIMIT 1000)
)
"""

report_notebook_ipynb = json.dumps(
    {
        'cells': [
            {
                'cell_type': 'code',
                'execution_count': None,
                'id': 'nb_report_1',
                'metadata': {},
                'outputs': [],
                'source': [
                    'from google.cloud import bigquery\n',
                    'client = bigquery.Client()\n',
                    "df = client.query('SELECT predicted_churned, COUNT(*) AS n_users FROM `bq_ml.ga4_churn_bp_scoring` GROUP BY 1').to_dataframe()\n",
                    'print(df)',
                ],
            }
        ],
        'metadata': {},
        'nbformat': 4,
        'nbformat_minor': 5,
    },
    indent=1,
)

report_notebook_js = """notebook({
  name: "ga4_churn_bp_notebook_report",
  filename: "ga4_churn_bp_report.ipynb",
  dependencyTargets: [{ name: "ga4_churn_bp_scoring" }],
  description: "Downstream Colab Enterprise notebook summarizing batch churn predictions"
});
"""

pipeline_files = {
    'workflow_settings.yaml': workflow_settings,
    'definitions/ga4_churn_bp_raw_events.sqlx': raw_events_sqlx,
    'definitions/ga4_churn_bp_features.sqlx': features_sqlx,
    'definitions/test_features_pass.sqlx': test_features_pass_sqlx,
    'definitions/test_features_fail.sqlx': test_features_fail_sqlx,
    'definitions/ga4_churn_bp_model.sqlx': model_sqlx,
    'definitions/ga4_churn_bp_quality_gate.sqlx': quality_gate_sqlx,
    'definitions/ga4_churn_bp_scoring.sqlx': scoring_sqlx,
    'definitions/ga4_churn_bp_report.ipynb': report_notebook_ipynb,
    'definitions/ga4_churn_bp_report.js': report_notebook_js,
}

for path, contents in pipeline_files.items():
    dataform_client.write_file(
        request=dataform_v1.WriteFileRequest(
            workspace=workspace.name,
            path=path,
            contents=contents.encode('utf-8'),
        )
    )
print(f'Wrote {len(pipeline_files)} files to the workspace')
```

---
## Step 3 — Compile with `lineage_enabled=True` and inspect the resolved DAG

We compile the workspace with `CodeCompilationConfig(lineage_enabled=True)` (GA `2026-11-12` Knowledge Catalog table-level lineage).

**Verified live client nuance (`bigqueryUnitTest` on REST vs protobuf):**
- The `google-cloud-dataform` Python client's `CompilationResultAction` protobuf schema includes `.relation`, `.operations`, `.assertion`, `.declaration`, `.notebook`, and `.data_preparation`, but does not yet expose a typed `.bigquery_unit_test` attribute.
- Fetching `GET https://dataform.googleapis.com/v1/{compilation_result.name}:query` via an authenticated `AuthorizedSession` returns the complete JSON action list — including the compiled `bigqueryUnitTest` objects (`displayName`, `testQuery`, and `expectedOutputQuery`) where Dataform has automatically substituted `${ref("ga4_churn_bp_raw_events")}` with the inline mock `input` subquery.

```python
from google.auth.transport.requests import AuthorizedSession

compilation_result = dataform_client.create_compilation_result(
    parent=repository.name,
    compilation_result=dataform_v1.CompilationResult(
        workspace=workspace.name,
        code_compilation_config=dataform_v1.CodeCompilationConfig(
            lineage_enabled=True,
        ),
    ),
)
print('Compilation result:', compilation_result.name)
print('Compilation errors:', len(compilation_result.compilation_errors))

creds, _ = google.auth.default(scopes=['https://www.googleapis.com/auth/cloud-platform'])
authed_session = AuthorizedSession(creds)
raw_actions = authed_session.get(
    f'https://dataform.googleapis.com/v1/{compilation_result.name}:query'
).json().get('compilationResultActions', [])

print('\nResolved pipeline & test actions:')
unit_tests = []
for action in raw_actions:
    name = action['target']['name']
    if 'relation' in action:
        rel_type = action['relation'].get('relationType', 'RELATION')
        deps = [d['name'] for d in action['relation'].get('dependencyTargets', [])]
        print(f'  {name:35s} relation ({rel_type:5s})  deps={deps}')
    elif 'operations' in action:
        deps = [d['name'] for d in action['operations'].get('dependencyTargets', [])]
        print(f'  {name:35s} operations        deps={deps}')
    elif 'assertion' in action:
        deps = [d['name'] for d in action['assertion'].get('dependencyTargets', [])]
        print(f'  {name:35s} assertion         deps={deps}')
    elif 'notebook' in action:
        deps = [d['name'] for d in action['notebook'].get('dependencyTargets', [])]
        print(f'  {name:35s} notebook (.ipynb) deps={deps}')
    elif 'bigqueryUnitTest' in action:
        ut = action['bigqueryUnitTest']
        unit_tests.append(ut)
        print(f'  {name:35s} bigqueryUnitTest  (hermetic SQL unit test)')
```

---
## Step 4 — Execute the SQL Unit Tests (`type: "test"`, GA `2026-09-17`) with `0` bytes billed

**Verified live API behavior:** `create_workflow_invocation` only executes materialization and operation nodes (`relation`, `operations`, `assertion`, `notebook`); passing a `type: "test"` target to `create_workflow_invocation` returns `400 At least one action must be selected for execution`.

Instead, BigQuery Studio's **"Run tests"** button (and `dataform test` in CI) executes each compiled `bigqueryUnitTest` by comparing its `testQuery` (which runs the real feature SQL over the inline mock `input` subquery) against its `expectedOutputQuery` via symmetric set difference (`EXCEPT DISTINCT`). Because all inputs are inline `SELECT` literals, **every unit test scans `0` bytes and bills `$0.00`**:
- `test_features_pass` $\to$ **`PASSED`** (`0` mismatched rows)
- `test_features_fail` $\to$ **`FAILED`** (`2` mismatched rows: actual `churned = TRUE` vs expected `churned = FALSE`)

```python
for ut in sorted(unit_tests, key=lambda u: u['displayName']):
    diff_sql = f"""
    WITH actual AS ({ut['testQuery']}),
    expected AS ({ut['expectedOutputQuery']})
    SELECT 'actual_minus_expected' AS diff_side, *
    FROM (SELECT * FROM actual EXCEPT DISTINCT SELECT * FROM expected)
    UNION ALL
    SELECT 'expected_minus_actual' AS diff_side, *
    FROM (SELECT * FROM expected EXCEPT DISTINCT SELECT * FROM actual)
    """
    job = client.query(diff_sql, job_config=bigquery.QueryJobConfig(use_query_cache=False))
    diff_df = job.to_dataframe()
    status = 'PASSED' if diff_df.empty else f'FAILED ({len(diff_df)} diff rows)'
    print(f"{ut['displayName']:25s} -> {status} | bytes_billed={job.total_bytes_billed}")
    if not diff_df.empty:
        display(diff_df[['diff_side', 'user_pseudo_id', 'did_purchase', 'churned']])
```

---
## Step 5 — Run the SQL + BQML Pipeline to `SUCCEEDED` (`WorkflowInvocation`)

In `pipelines/dataform` (`pipelines/dataform/`), we included an intentionally impossible `roc_auc < 0.99` assertion to prove that a failed assertion causes downstream `scoring` to be `SKIPPED`.

Here, we execute the realistic `roc_auc >= 0.60` quality gate (`ga4_churn_bp_quality_gate`) by targeting `ga4_churn_bp_scoring` with `transitive_dependencies_included=True` and `transitive_dependents_included=False`. This runs the 5-action SQL + BQML chain (`ga4_churn_bp_raw_events` $\to$ `ga4_churn_bp_features` $\to$ `ga4_churn_bp_model` $\to$ `ga4_churn_bp_quality_gate` $\to$ `ga4_churn_bp_scoring`) end-to-end to **`SUCCEEDED`** without requiring a persistent Colab Enterprise `NotebookRuntimeTemplate` for the optional downstream `.ipynb` node.

> **Executing `.ipynb` `notebook` nodes in production:** When your pipeline includes `notebook({...})` tasks in `WorkflowInvocation`, pass `default_notebook_runtime_options=dataform_v1.CodeCompilationConfig.NotebookRuntimeOptions(ai_platform_notebook_runtime_template='projects/.../notebookRuntimeTemplates/...', gcs_output_bucket='gs://...')` on `CodeCompilationConfig` so Colab Enterprise has a runtime template and GCS output bucket for headless `.ipynb` execution.

```python
import time
from google.api_core.exceptions import PermissionDenied

def start_invocation():
    return dataform_client.create_workflow_invocation(
        parent=repository.name,
        workflow_invocation=dataform_v1.WorkflowInvocation(
            compilation_result=compilation_result.name,
            invocation_config=dataform_v1.InvocationConfig(
                included_targets=[
                    dataform_v1.Target(
                        database=PROJECT_ID,
                        schema=DATASET_ID,
                        name='ga4_churn_bp_scoring',
                    )
                ],
                transitive_dependencies_included=True,
                transitive_dependents_included=False,
                service_account=runtime_service_account,
            ),
        ),
    )

for attempt in range(3):
    try:
        invocation = start_invocation()
        break
    except PermissionDenied:
        print(f'Permission not yet propagated (attempt {attempt + 1}/3) — waiting 60s...')
        time.sleep(60)
else:
    invocation = start_invocation()

print('Invocation:', invocation.name)

while True:
    invocation = dataform_client.get_workflow_invocation(name=invocation.name)
    state = invocation.state.name
    if state in ('SUCCEEDED', 'FAILED', 'CANCELLED'):
        break
    time.sleep(15)

print('Final invocation state:', state)
```

```python
action_results = dataform_client.query_workflow_invocation_actions(
    request=dataform_v1.QueryWorkflowInvocationActionsRequest(name=invocation.name)
)
for a in action_results:
    reason = f' — {a.failure_reason}' if a.failure_reason else ''
    print(f'{a.target.name:40s} {a.state.name}{reason}')
```

### Verify materialized predictions and enriched BigQuery metadata (GA `2026-10-01`)

Because `ga4_churn_bp_quality_gate` (`roc_auc >= 0.60`) passed, `ga4_churn_bp_scoring` (`dependOnDependencyAssertions: true`) ran and materialized 1,000 scored users—and BigQuery automatically received the table description, labels, and column descriptions declared in Step 2's `.sqlx` `config` blocks.

```python
# 1. Inspect the materialized predictions and model evaluation
eval_and_pred_sql = f"""
SELECT
  (SELECT ROUND(roc_auc, 4) FROM ML.EVALUATE(MODEL `{PROJECT_ID}.{DATASET_ID}.ga4_churn_bp_model`)) AS model_roc_auc,
  COUNT(*) AS scored_users,
  COUNTIF(predicted_churned) AS predicted_churners,
  COUNTIF(NOT predicted_churned) AS predicted_retained
FROM `{PROJECT_ID}.{DATASET_ID}.ga4_churn_bp_scoring`
"""
display(client.query(eval_and_pred_sql, job_config=bigquery.QueryJobConfig(use_query_cache=False)).to_dataframe())

# 2. Verify metadata enrichment (column descriptions propagated to INFORMATION_SCHEMA)
metadata_sql = f"""
SELECT table_name, column_name, data_type, description
FROM `{PROJECT_ID}.{DATASET_ID}.INFORMATION_SCHEMA.COLUMN_FIELD_PATHS`
WHERE table_name IN ('ga4_churn_bp_features', 'ga4_churn_bp_scoring')
  AND description IS NOT NULL
ORDER BY table_name, column_name
"""
display(client.query(metadata_sql).to_dataframe())
```

### Governance Preservation (`preserveGovernanceControls`, GA `2026-10-20`) & Concurrency Limits (GA `2026-11-09`)

Two additional 2026 BigQuery Studio Pipelines / Dataform capabilities are worth noting before scheduling a pipeline in production:
1. **`preserveGovernanceControls: true` (GA `2026-10-20`)**: Normally, when a pipeline rebuilds a table with `CREATE OR REPLACE TABLE`, existing BigQuery column-level policy tags, data masking policies, and row-access policies on that table are wiped. Setting `preserveGovernanceControls: true` in `workflow_settings.yaml` (or per-table `config`) instructs Dataform to preserve column- and row-level governance policies across table rebuilds. *(Note: do **not** place `preserve_governance_controls` inside `bigquery.additionalOptions`, which passes raw `OPTIONS(...)` directly to BigQuery DDL and fails with `Unknown option: preserve_governance_controls`.)*
2. **Action concurrency limits (GA `2026-11-09`)**: When a pipeline fans out across multiple `CREATE MODEL` or `AI.*` branches, configure a maximum concurrent task/action limit in the pipeline settings so parallel actions do not exhaust BigQuery reservation slots or Vertex AI RPM/TPM quotas.

---
## Step 6 — Commit to Git and configure a scheduled BigQuery Pipeline (`ReleaseConfig` + `WorkflowConfig`)

Whereas `pipelines/dataform` (`pipelines/dataform/`) stops after a one-off `WorkflowInvocation` on an uncommitted workspace, production BigQuery Studio Pipelines use a two-tier scheduling architecture on the repository's Git history:
1. **Commit workspace changes (`commit_workspace_changes`)** to the repository's `main` branch.
2. **`ReleaseConfig`** — pins or compiles a production `CompilationResult` from `main`.
   - **Verified live gotcha (`strictActAsChecks`)**: New first-party Dataform repositories enable `strictActAsChecks` by default, which rejects setting `cron_schedule` directly on `ReleaseConfig` (`400 Automatic release is not supported in first-party repositories that enabled strictActAsChecks`) because `ReleaseConfig` has no `service_account` field. Instead, pin `release_compilation_result=compilation_result.name` on `ReleaseConfig` and place the cron schedule + `service_account` on **`WorkflowConfig`**.
3. **`WorkflowConfig`** — schedules unattended `WorkflowInvocation` runs on a timezone-aware cron schedule (`0 6 * * *` `America/New_York`) using `invocation_config.service_account`. We set `disabled=True` here so it does not trigger between creation and the Cleanup cell below.

```python
# 1. Commit the workspace files to the repository's internal Git history ('main')
dataform_client.commit_workspace_changes(
    request=dataform_v1.CommitWorkspaceChangesRequest(
        name=workspace.name,
        author=dataform_v1.CommitAuthor(
            name='BigQuery Pipelines Demo',
            email_address='demo@example.com',
        ),
        commit_message='Add GA4 churn BigQuery Studio Pipeline with unit tests and metadata',
    )
)
print('Committed workspace changes to main branch')

# 2. Create a production ReleaseConfig pinned to our verified CompilationResult
release_config = dataform_client.create_release_config(
    parent=repository.name,
    release_config_id='production-release',
    release_config=dataform_v1.ReleaseConfig(
        git_commitish='main',
        release_compilation_result=compilation_result.name,
        code_compilation_config=dataform_v1.CodeCompilationConfig(
            lineage_enabled=True,
        ),
    ),
)
print('Created ReleaseConfig:', release_config.name)

# 3. Create a cron-scheduled WorkflowConfig (disabled=True for safe demo teardown)
workflow_config = dataform_client.create_workflow_config(
    parent=repository.name,
    workflow_config_id='daily-ga4-churn-pipeline',
    workflow_config=dataform_v1.WorkflowConfig(
        release_config=release_config.name,
        cron_schedule='0 6 * * *',
        time_zone='America/New_York',
        invocation_config=dataform_v1.InvocationConfig(
            included_targets=[
                dataform_v1.Target(
                    database=PROJECT_ID,
                    schema=DATASET_ID,
                    name='ga4_churn_bp_scoring',
                )
            ],
            transitive_dependencies_included=True,
            service_account=runtime_service_account,
        ),
        disabled=True,
    ),
)
print('Created WorkflowConfig:', workflow_config.name)
print('Schedule:', workflow_config.cron_schedule, f'({workflow_config.time_zone}), disabled={workflow_config.disabled}')
```

---
## Related content

- `pipelines/dataform` (`pipelines/dataform/`) — the companion walkthrough on the same `google.cloud.dataform_v1` API focusing on `.sqlx` dependency graphs and a deliberately-failing `assertion` that halts downstream scoring (`SKIPPED`).
- `pipelines/scheduled_queries` (`pipelines/scheduled_queries/`) — schedules a single procedural SQL script via BigQuery Data Transfer Service (`TransferConfig`) when you don't need multi-node DAGs, unit tests, or `.ipynb` tasks.
- `pipelines/cloud_workflows` (`pipelines/cloud_workflows/`) — Google Cloud Workflows (`workflows.googleapis.com`), the serverless YAML state-machine orchestrator that prompted Google to rename BigQuery Studio's *"BigQuery Workflows"* to **"BigQuery Pipelines"**.
- `workflows/ga4_churn_prediction` (`workflows/ga4_churn_prediction/`) — the GA4 churn workflow this pipeline operationalizes.
