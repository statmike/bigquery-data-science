> **Source (`statmike/bigquery-data-science`):** **Notebook:** [`bigquery-ai/functions/ml_generate_embedding/ml_generate_embedding.ipynb`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ai/functions/ml_generate_embedding/ml_generate_embedding.ipynb) · **SQL:** [`bigquery-ai/functions/ml_generate_embedding/ml_generate_embedding.sql`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ai/functions/ml_generate_embedding/ml_generate_embedding.sql)

# ML.GENERATE_EMBEDDING — BigQuery AI Functions

`ML.GENERATE_EMBEDDING` is the legacy predecessor to `AI.GENERATE_EMBEDDING`. Same capabilities but with `ml_generate_embedding_` prefixed column names. **Google recommends using `AI.GENERATE_EMBEDDING` for new queries.**

**When to use it:**
- You have existing code that uses ML.GENERATE_EMBEDDING and need to maintain it
- You need the `flatten_json_output` parameter

**Alternatives:**
- `functions/ai_generate_embedding` (`AI.GENERATE_EMBEDDING`) — Recommended replacement — same capabilities, cleaner column names
- `functions/ai_embed` (`AI.EMBED`) — Scalar function, no model required

**Multimodal:** Supports image and video input via `reference/unstructured-data-infrastructure.md#objectref-and-objectrefruntime-schema-reference` (ObjectRef). Pass `ObjectRef` values in the `content` column to create multimodal embeddings.

**References:** `RESOURCES.md` (Full syntax reference) | [Official documentation](https://cloud.google.com/bigquery/docs/reference/standard-sql/bigqueryml-syntax-generate-embedding) | `setup` (Setup guide)

---
## Setup

Set your project and location, authenticate, and create a temporary dataset for this notebook.

> This function requires a connection and a remote model. The cells below create them if they don't exist. See the `setup` (Setup Reference) for details.

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
DATASET_ID = 'bq_ai_functions'  # Shared dataset across all notebooks
CONNECTION_ID = 'bq_ai_functions'  # Shared connection
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

```python
import subprocess as _sp, json as _json

# Create connection (idempotent)
_sp.run(['bq', 'mk', '--connection', '--location', LOCATION,
         '--connection_type', 'CLOUD_RESOURCE',
         '--project_id', PROJECT_ID, CONNECTION_ID],
        capture_output=True, text=True)

# Get service account and grant Vertex AI User role
r = _sp.run(['bq', 'show', '--connection', '--format=json',
             '--project_id', PROJECT_ID, '--location', LOCATION, CONNECTION_ID],
            capture_output=True, text=True, check=True)
sa = _json.loads(r.stdout)['cloudResource']['serviceAccountId']
_sp.run(['gcloud', 'projects', 'add-iam-policy-binding', PROJECT_ID,
         f'--member=serviceAccount:{sa}', '--role=roles/aiplatform.user', '--quiet'],
        capture_output=True, text=True)
print(f'Connection {CONNECTION_ID} ready (SA: {sa})')
```

```python
# Create remote embedding model (idempotent)
client.query(f'''
CREATE OR REPLACE MODEL `{PROJECT_ID}.{DATASET_ID}.embedding_text`
  REMOTE WITH CONNECTION `{PROJECT_ID}.{LOCATION}.{CONNECTION_ID}`
  OPTIONS (endpoint = \'gemini-embedding-2\')
''').result()
print('Model embedding_text ready')
```

---
## Examples — SQL

Progressive examples from simplest to most advanced. Each cell adds one new concept.

### 1. Basic text embedding

Column names are prefixed with `ml_generate_embedding_`. The `flatten_json_output` parameter defaults to `TRUE`.

> **Note:** `gemini-embedding-2` returns `ml_generate_embedding_result` (3,072 dimensions by default) and `ml_generate_embedding_status`, and omits `ml_generate_embedding_statistics` (which is only returned by legacy text models such as `text-embedding-005` and `gemini-embedding-001`).

```python
query = f'''
SELECT content,
  ARRAY_LENGTH(ml_generate_embedding_result) AS dims,
  ml_generate_embedding_status
FROM ML.GENERATE_EMBEDDING(
  MODEL `{PROJECT_ID}.{DATASET_ID}.embedding_text`,
  (SELECT text AS content
   FROM UNNEST(['BigQuery is a data warehouse.', 'Cloud computing scales.']) AS text)
)
'''
client.query(query).to_dataframe()
```

### 2. Column name comparison with AI.GENERATE_EMBEDDING

```python
# ML.GENERATE_EMBEDDING columns
query_ml = f'''
SELECT *
FROM ML.GENERATE_EMBEDDING(
  MODEL `{PROJECT_ID}.{DATASET_ID}.embedding_text`,
  (SELECT 'test' AS content)
)
'''
df_ml = client.query(query_ml).to_dataframe()
print('ML.GENERATE_EMBEDDING columns:', list(df_ml.columns))

# AI.GENERATE_EMBEDDING columns
query_ai = f'''
SELECT *
FROM AI.GENERATE_EMBEDDING(
  MODEL `{PROJECT_ID}.{DATASET_ID}.embedding_text`,
  (SELECT 'test' AS content)
)
'''
df_ai = client.query(query_ai).to_dataframe()
print('AI.GENERATE_EMBEDDING columns:', list(df_ai.columns))
```

### 3. Reducing dimensions with `output_dimensionality`

`gemini-embedding-2` produces unified, task-agnostic 3,072-dimension embeddings and **rejects `task_type` and `title`** (failing with `400 INVALID_ARGUMENT` if `task_type` is supplied; `task_type` such as `RETRIEVAL_DOCUMENT` / `RETRIEVAL_QUERY` is only used on legacy models like `gemini-embedding-001` and `text-embedding-005`).

Instead, `gemini-embedding-2` supports Matryoshka dimension reduction via `output_dimensionality` in the options `STRUCT`. Reducing from 3,072 to `768` dimensions keeps vectors within BigQuery's `<= 2,000`-dimension limit for `CREATE VECTOR INDEX`:

```python
query = f'''
SELECT content,
  ARRAY_LENGTH(ml_generate_embedding_result) AS dims,
  ml_generate_embedding_status
FROM ML.GENERATE_EMBEDDING(
  MODEL `{PROJECT_ID}.{DATASET_ID}.embedding_text`,
  (SELECT text AS content
   FROM UNNEST(['BigQuery', 'Cloud Functions', 'Cloud Storage']) AS text),
  STRUCT(768 AS output_dimensionality, TRUE AS flatten_json_output)
)
'''
client.query(query).to_dataframe()
```

### Multimodal embeddings

For multimodal embedding examples (images, video), see the `functions/ai_generate_embedding` (`AI.GENERATE_EMBEDDING`) notebook, which demonstrates the same functionality with cleaner column names.

---
## Examples — `%%bigquery` Magics

The same examples using IPython magic commands. Magics let you write SQL directly in notebook cells without Python string wrapping.

Key patterns:
- `%%bigquery` — run SQL, display results inline
- `%%bigquery df` — run SQL, capture results into a pandas DataFrame

### ML.GENERATE_EMBEDDING with `%%bigquery`

```sql
%%bigquery --project {PROJECT_ID}

SELECT content, ARRAY_LENGTH(ml_generate_embedding_result) AS dims
FROM ML.GENERATE_EMBEDDING(
  MODEL `bq_ai_functions.embedding_text`,
  (SELECT text AS content FROM UNNEST(['Machine learning', 'Deep learning']) AS text)
)
```

---
## Examples — BigFrames

BigFrames has two ways to generate embeddings:
- **`bigframes.bigquery.ai.generate_embedding` (`bbq.ai.generate_embedding`) / `bbq.ai.embed` (Recommended):** Wraps `AI.GENERATE_EMBEDDING` / `AI.EMBED` directly and supports `gemini-embedding-2` with zero client-side warnings.
- **`bigframes.ml.llm.TextEmbeddingGenerator` (Legacy wrapper):** In `bigframes 2.51.0`, `TextEmbeddingGenerator` validates `model_name` against a hardcoded client-side tuple `_TEXT_EMBEDDING_ENDPOINTS = ('text-embedding-005', 'text-embedding-004', 'text-multilingual-embedding-002')` and its `.predict()` method queries `ml_generate_embedding_statistics` (which `gemini-embedding-2` omits). Use `'text-embedding-005'` if maintaining existing `TextEmbeddingGenerator` code, and prefer `bbq.ai.embed` or `bbq.ai.generate_embedding` for new code.

```python
import bigframes.pandas as bpd
import bigframes.bigquery as bbq

bpd.options.bigquery.project = PROJECT_ID
bpd.options.bigquery.location = LOCATION
```

### Using `bbq.ai.generate_embedding` (recommended) and legacy `TextEmbeddingGenerator`

```python
from bigframes.ml.llm import TextEmbeddingGenerator

df = bpd.DataFrame({'content': ['BigQuery', 'Cloud Storage', 'Cloud Functions']})

# Recommended: bbq.ai.generate_embedding with gemini-embedding-2
model_name = f'{PROJECT_ID}.{DATASET_ID}.embedding_text'
result = bbq.ai.generate_embedding(model_name, df)
print('bbq.ai.generate_embedding (gemini-embedding-2):')
print(result[['content', 'status']].to_pandas())

# Legacy: bigframes.ml.llm.TextEmbeddingGenerator (uses _TEXT_EMBEDDING_ENDPOINTS allowlist)
legacy_embedder = TextEmbeddingGenerator(
    model_name='text-embedding-005',
    connection_name=f'{PROJECT_ID}.{LOCATION}.{CONNECTION_ID}',
)
legacy_df = legacy_embedder.predict(df)
legacy_df[['content', 'ml_generate_embedding_status']].to_pandas()
```
