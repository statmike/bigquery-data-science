> **Source (`statmike/bigquery-data-science`):** **Notebook:** [`bigquery-ai/workflows/document_rag/document_rag.ipynb`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ai/workflows/document_rag/document_rag.ipynb)

# Document RAG — BigQuery AI Functions

A complete document-based Retrieval-Augmented Generation (RAG) pipeline built entirely in BigQuery SQL:

1. **Chunk** real PDFs into layout-aware sections with `AI.CHUNK_DOCUMENT`
2. **Embed** document chunks with `AI.EMBED` (`text-embedding-005`)
3. **Search** for relevant chunks with `VECTOR_SEARCH`
4. **Answer** questions with `AI.GENERATE` (`gemini-2.5-flash`), grounded in retrieved chunks with page and chunk citations

**What this demonstrates:**
- Building an end-to-end PDF RAG pipeline in BigQuery SQL with zero manual Document AI processor setup
- Layout-aware chunking (`chunk_size => 250`) across 20 single-page invoices and a multi-page policy document, preserving `chunk_id`, `start_page`, and `end_page` provenance
- Enforcing `AI.CHUNK_DOCUMENT`'s three-way `status` contract (`WHERE status = ''`) before embedding
- Comparing Object Table input against inline `OBJ.MAKE_REF` and GCS URI wildcard chunking
- Asymmetric embedding (`RETRIEVAL_DOCUMENT` vs `RETRIEVAL_QUERY`) and page-cited grounded generation vs ungrounded direct generation

**Functions used:** `functions/ai_chunk_document` (`AI.CHUNK_DOCUMENT`) | `functions/ai_embed` (`AI.EMBED`) | `functions/vector_search` (`VECTOR_SEARCH`) | `functions/ai_generate` (`AI.GENERATE`)

**Prerequisites:** `setup` (Setup guide) | `reference/document-processing.md` (Document processing reference) | `RESOURCES.md` (Function reference)

---
## Setup

Set your project and location, authenticate, and configure shared resources.

> This workflow uses: (1) a **Cloud resource connection** with Cloud Storage, Document AI, and Vertex AI roles, and (2) **Cloud Storage** + an **object table** pointing to the staged PDFs. Unlike `ML.PROCESS_DOCUMENT`, `AI.CHUNK_DOCUMENT` requires **no manual Document AI processor creation** — BigQuery automatically provisions and reuses a zero-idle-fee `bq-created-layout-parser` processor on first run. See the `setup` (Setup Reference) and `reference/document-processing.md` (Document Processing Reference) for details.

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
LOCATION = 'US'  # BigQuery dataset location (AI.CHUNK_DOCUMENT supports US and EU regions)
DATASET_ID = 'bq_ai_functions'  # Shared dataset across all notebooks
CONNECTION_ID = 'bq_ai_functions'  # Shared Cloud resource connection
BUCKET = PROJECT_ID  # GCS bucket for document storage
```

### Environment

> **Already set up the project environment?** Skip to [Step 1](#step-1--chunk-documents-with-aichunk_document).  
> **Running standalone** (Colab, Colab Enterprise, Vertex AI Workbench)? Run the cells below to install packages, authenticate, and configure the shared dataset, connection, and bucket. See the `setup` (Setup Reference) for details.

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
import json as _json
import re as _re
import subprocess as _sp
import time as _time
from google.cloud import storage

# 1. Ensure required APIs are enabled
REQUIRED_APIS = [
    'bigquery.googleapis.com',
    'bigqueryconnection.googleapis.com',
    'aiplatform.googleapis.com',
    'documentai.googleapis.com',
    'storage.googleapis.com',
]
enabled_out = _sp.run(
    ['gcloud', 'services', 'list', '--enabled', f'--project={PROJECT_ID}', '--format=value(config.name)'],
    capture_output=True, text=True, check=True,
)
enabled_apis = set(enabled_out.stdout.split())
for api in [a for a in REQUIRED_APIS if a not in enabled_apis]:
    _sp.run(['gcloud', 'services', 'enable', api, f'--project={PROJECT_ID}'], capture_output=True, text=True, check=True)

# 2. Create Cloud resource connection (idempotent)
_sp.run(
    ['bq', 'mk', '--connection', '--location', LOCATION,
     '--connection_type', 'CLOUD_RESOURCE', '--project_id', PROJECT_ID, CONNECTION_ID],
    capture_output=True, text=True,
)
r = _sp.run(
    ['bq', 'show', '--connection', '--format=json',
     '--project_id', PROJECT_ID, '--location', LOCATION, CONNECTION_ID],
    capture_output=True, text=True, check=True,
)
sa = _json.loads(r.stdout)['cloudResource']['serviceAccountId']
sa_display = _re.sub(r'bqcx-\d+-', 'bqcx-000000000000-', sa)

# 3. Grant required roles to the connection service account
# roles/documentai.editor allows first-run auto-creation of bq-created-layout-parser (viewer suffices thereafter)
REQUIRED_ROLES = [
    'roles/serviceusage.serviceUsageConsumer',
    'roles/bigquery.connectionUser',
    'roles/storage.objectViewer',
    'roles/documentai.editor',
    'roles/aiplatform.user',
]
policy_out = _sp.run(
    ['gcloud', 'projects', 'get-iam-policy', PROJECT_ID,
     '--flatten=bindings[].members', f'--filter=bindings.members:{sa}',
     '--format=value(bindings.role)'],
    capture_output=True, text=True, check=True,
)
held_roles = set(policy_out.stdout.split())
missing_roles = [role for role in REQUIRED_ROLES if role not in held_roles]
for role in missing_roles:
    _sp.run(
        ['gcloud', 'projects', 'add-iam-policy-binding', PROJECT_ID,
         f'--member=serviceAccount:{sa}', f'--role={role}', '--condition=None', '--quiet'],
        capture_output=True, text=True, check=True,
    )
if missing_roles:
    print(f'Granted {len(missing_roles)} new IAM role(s); waiting 60s for propagation...')
    _time.sleep(60)

# 4. Ensure GCS bucket exists
gcs = storage.Client(project=PROJECT_ID)
bucket = gcs.bucket(BUCKET)
if not bucket.exists():
    bucket = gcs.create_bucket(BUCKET, location=LOCATION)

print(f'Connection {CONNECTION_ID} ready (SA: {sa_display})')
print(f'Bucket gs://{BUCKET} ready')
```

### Upload documents and create object table

Stage **21 PDF documents** under `gs://{BUCKET}/bq_ai_functions/document_rag/` and register an external object table (`workflow_docrag_objects`):

- **20 single-page vendor invoices** (`invoice_001.pdf` – `invoice_020.pdf`) from `data/documents` (`data/documents/invoices/`) (fetched automatically from GitHub if running standalone in Colab)
- **1 multi-page policy handbook** (`ap_vendor_policy.pdf`, 3 pages) rendered in memory so the corpus includes multi-chunk (`chunk_id > 1`) and multi-page (`start_page` / `end_page` across pages 1–3) sections alongside single-page transactional records

```python
import io
import urllib.request
from pathlib import Path
from tqdm import tqdm

prefix = 'bq_ai_functions/document_rag'

# 1. Stage 20 sample invoice PDFs (local checkout with GitHub raw fallback for standalone Colab)
candidate_dirs = [
    Path('../../data/documents/invoices'),
    Path('bigquery-ai/data/documents/invoices'),
    Path('data/documents/invoices'),
]
data_dir = next((d for d in candidate_dirs if d.exists()), None)

uploaded, skipped = 0, 0
for i in tqdm(range(1, 21), desc='Staging invoices'):
    fname = f'invoice_{i:03d}.pdf'
    blob = bucket.blob(f'{prefix}/{fname}')
    if blob.exists():
        skipped += 1
        continue
    if data_dir is not None:
        blob.upload_from_filename(str(data_dir / fname), content_type='application/pdf')
    else:
        raw_url = f'https://raw.githubusercontent.com/statmike/bigquery-data-science/main/bigquery-ai/data/documents/invoices/{fname}'
        with urllib.request.urlopen(raw_url) as resp:
            blob.upload_from_string(resp.read(), content_type='application/pdf')
    uploaded += 1

# 2. Render and stage a deterministic 3-page Accounts Payable policy PDF for multi-page chunking
policy_blob = bucket.blob(f'{prefix}/ap_vendor_policy.pdf')
if policy_blob.exists():
    skipped += 1
else:
    page_sections = [
        (
            '1. Invoice Submission & Purchase Order Matching',
            'All supplier invoices must be submitted in PDF format to the Accounts Payable portal '
            'with a valid invoice number, issue date, due date, itemized line descriptions, and billing entity. '
            + ('Purchase order matching verifies contracted unit rates, delivered quantities, and tax exemptions before posting. ' * 12),
        ),
        (
            '2. Standard Payment Terms & Late Fee Governance',
            'Default payment terms across technology and event vendors are Net 30 from the invoice issue date '
            'unless superseded by a master services agreement specifying Net 15 or Net 45 settlement. '
            + ('Early-payment discounts of 2 percent 10 Net 30 require treasury confirmation and automated remittance scheduling. ' * 12),
        ),
        (
            '3. Approval Thresholds & Discrepancy Escalation',
            'Invoices up to $10,000 require department manager approval; invoices from $10,000.01 to $25,000 require '
            'Director sign-off; any invoice exceeding $25,000 requires VP of Finance approval prior to disbursement. '
            'Billing discrepancies or duplicate reference numbers must be reported to the vendor within 5 business days. '
            + ('Quarterly audit sampling reconciles disbursed ledger totals against archived Cloud Storage PDFs. ' * 10),
        ),
    ]
    try:
        from weasyprint import HTML
        html_body = ''.join(
            f'<div style="{"page-break-before: always;" if idx > 0 else ""}">'
            f'<h1>Accounts Payable &amp; Vendor Billing Policy</h1><h2>{heading}</h2><p>{body}</p></div>'
            for idx, (heading, body) in enumerate(page_sections)
        )
        policy_pdf_bytes = HTML(
            string=f'<!DOCTYPE html><html><head><style>@page {{ size: letter; margin: 1in; }}</style></head><body>{html_body}</body></html>'
        ).write_pdf()
    except Exception:
        import textwrap
        import matplotlib.pyplot as plt
        from matplotlib.backends.backend_pdf import PdfPages
        buf = io.BytesIO()
        with PdfPages(buf) as pdf:
            for heading, body in page_sections:
                fig = plt.figure(figsize=(8.5, 11))
                fig.text(0.1, 0.9, 'Accounts Payable & Vendor Billing Policy', fontsize=15, weight='bold')
                fig.text(0.1, 0.84, heading, fontsize=12, weight='bold')
                fig.text(0.1, 0.78, '\n'.join(textwrap.wrap(body, width=82)), fontsize=10, va='top')
                pdf.savefig(fig)
                plt.close(fig)
        policy_pdf_bytes = buf.getvalue()

    policy_blob.upload_from_string(policy_pdf_bytes, content_type='application/pdf')
    uploaded += 1

print(f'Uploaded {uploaded} documents, skipped {skipped} (already exist)')
print(f'Location: gs://{BUCKET}/{prefix}/')
```

```python
client.query(f"""
CREATE OR REPLACE EXTERNAL TABLE `{PROJECT_ID}.{DATASET_ID}.workflow_docrag_objects`
WITH CONNECTION `{PROJECT_ID}.{LOCATION}.{CONNECTION_ID}`
OPTIONS (
  object_metadata = 'SIMPLE',
  uris = ['gs://{BUCKET}/{prefix}/*.pdf']
)
""").result()

df = client.query(f"""
  SELECT uri, content_type, size
  FROM `{PROJECT_ID}.{DATASET_ID}.workflow_docrag_objects`
  ORDER BY uri
""").to_dataframe()
print(f'Object table workflow_docrag_objects ready — {len(df)} documents')
df.head(6)
```

---
## Step 1 — Chunk documents with AI.CHUNK_DOCUMENT

`AI.CHUNK_DOCUMENT` reads documents from the object table, parses layout structure (headings, paragraphs, tables) via BigQuery's managed `bq-created-layout-parser` processor, and splits long documents into chunks up to `chunk_size` tokens (`1`–`2000`, default `1000`).

Two details matter in every production pipeline:
1. **Matching `connection_id`:** When reading an object table (or `OBJ.MAKE_REF` subquery), `connection_id` in `AI.CHUNK_DOCUMENT` must match the connection bound to those object references.
2. **Three-way `status` filtering:** `AI.CHUNK_DOCUMENT` sets `status = ''` (empty string) on success, a non-empty error message on corrupt or unsupported files, and `NULL` when an `ObjectRef` points to a missing GCS object. Always filter `WHERE status = ''` before downstream embedding — filtering `WHERE status IS NULL` would discard every valid chunk.

Below we materialize the raw chunking output with `chunk_size => 250`, verify the per-row `status` summary, and keep clean chunks for Step 2.

```python
raw_chunks = client.query(f"""
WITH raw AS (
  SELECT
    uri,
    chunk_id,
    start_page,
    end_page,
    content,
    status
  FROM AI.CHUNK_DOCUMENT(
    TABLE `{PROJECT_ID}.{DATASET_ID}.workflow_docrag_objects`,
    connection_id => '{PROJECT_ID}.{LOCATION}.{CONNECTION_ID}',
    chunk_size => 250
  )
)
SELECT
  COUNT(*) AS total_rows,
  COUNTIF(status = '') AS valid_chunks,
  COUNTIF(status != '') AS parse_errors,
  COUNTIF(status IS NULL) AS missing_refs
FROM raw
""").to_dataframe()
print(
    f"Status check — total_rows: {raw_chunks.iloc[0]['total_rows']}, "
    f"valid_chunks (status = ''): {raw_chunks.iloc[0]['valid_chunks']}, "
    f"parse_errors: {raw_chunks.iloc[0]['parse_errors']}, "
    f"missing_refs: {raw_chunks.iloc[0]['missing_refs']}"
)

# Persist verified chunks (status = '') so downstream steps do not re-parse PDFs
client.query(f"""
CREATE OR REPLACE TABLE `{PROJECT_ID}.{DATASET_ID}.workflow_docrag_chunks` AS
SELECT
  uri,
  chunk_id,
  start_page,
  end_page,
  content
FROM AI.CHUNK_DOCUMENT(
  TABLE `{PROJECT_ID}.{DATASET_ID}.workflow_docrag_objects`,
  connection_id => '{PROJECT_ID}.{LOCATION}.{CONNECTION_ID}',
  chunk_size => 250
)
WHERE status = ''
""").result()

stats = client.query(f"""
  SELECT
    COUNT(*) AS total_chunks,
    COUNT(DISTINCT uri) AS documents,
    MAX(chunk_id) AS max_chunks_in_doc,
    MAX(end_page) AS max_page_seen
  FROM `{PROJECT_ID}.{DATASET_ID}.workflow_docrag_chunks`
""").to_dataframe()
row = stats.iloc[0]
print(
    f"Persisted {row['total_chunks']} chunks across {row['documents']} documents "
    f"(up to {row['max_chunks_in_doc']} chunks and page {row['max_page_seen']} in a single PDF)"
)
```

```python
# Inspect multi-page policy chunks alongside single-page invoice chunks
client.query(f"""
  SELECT
    REGEXP_EXTRACT(uri, r'[^/]+$') AS document,
    chunk_id,
    start_page,
    end_page,
    LEFT(REPLACE(content, '\\n', ' '), 160) AS content_preview
  FROM `{PROJECT_ID}.{DATASET_ID}.workflow_docrag_chunks`
  ORDER BY
    CASE WHEN ENDS_WITH(uri, 'ap_vendor_policy.pdf') THEN 0 ELSE 1 END,
    uri,
    chunk_id
  LIMIT 8
""").to_dataframe()
```

### Alternative: Inline `ObjectRef` and URI wildcard — skip the object table

You don't need to create an external object table for ad-hoc document chunking. `AI.CHUNK_DOCUMENT` also accepts:
- **An inline `ObjectRef` subquery** (`SELECT uri, OBJ.MAKE_REF(uri, 'connection') AS ref FROM ...`), which returns the 5 chunk columns (`chunk_id`, `start_page`, `end_page`, `content`, `status`) **plus** whatever passthrough columns your subquery selects (if you omit `uri` from the subquery `SELECT`, read `ref.uri` instead).
- **A Cloud Storage URI or wildcard string** (`'gs://bucket/path/*.pdf'`), which returns the same 13 columns as an object table.

```python
# Ad-hoc inline ObjectRef subquery over 3 specific files — no object table required
sample_uris = [
    f'gs://{BUCKET}/{prefix}/ap_vendor_policy.pdf',
    f'gs://{BUCKET}/{prefix}/invoice_001.pdf',
    f'gs://{BUCKET}/{prefix}/invoice_003.pdf',
]
uris_sql = ', '.join(f"'{u}'" for u in sample_uris)

query = f"""
SELECT
  REGEXP_EXTRACT(uri, r'[^/]+$') AS document,
  chunk_id,
  start_page,
  end_page,
  LEFT(REPLACE(content, '\\n', ' '), 140) AS content_preview
FROM AI.CHUNK_DOCUMENT(
  (SELECT
    uri,
    OBJ.MAKE_REF(uri, '{PROJECT_ID}.{LOCATION}.{CONNECTION_ID}') AS ref
  FROM UNNEST([{uris_sql}]) AS uri),
  connection_id => '{PROJECT_ID}.{LOCATION}.{CONNECTION_ID}',
  chunk_size => 250
)
WHERE status = ''
ORDER BY document, chunk_id
LIMIT 6
"""
df = client.query(query).to_dataframe()
print(f'Inline ObjectRef approach: returned {len(df)} preview rows across {df["document"].nunique()} documents')
df
```

---
## Step 2 — Embed chunks with AI.EMBED

Generate `768`-dimensional vectors for every persisted chunk using `text-embedding-005` with `task_type => 'RETRIEVAL_DOCUMENT'`. Pairing `RETRIEVAL_DOCUMENT` at index time with `RETRIEVAL_QUERY` at search time aligns short user questions with longer document passages (asymmetric semantic search).

```python
query = f"""
CREATE OR REPLACE TABLE `{PROJECT_ID}.{DATASET_ID}.workflow_docrag_embedded` AS
SELECT
  uri,
  chunk_id,
  start_page,
  end_page,
  content,
  (AI.EMBED(
    content => content,
    endpoint => 'text-embedding-005',
    task_type => 'RETRIEVAL_DOCUMENT'
  )).result AS embedding
FROM `{PROJECT_ID}.{DATASET_ID}.workflow_docrag_chunks`
WHERE content IS NOT NULL AND LENGTH(TRIM(content)) > 0
"""
client.query(query).result()

verify = client.query(f"""
  SELECT COUNT(*) AS chunks, ARRAY_LENGTH(embedding) AS dims
  FROM `{PROJECT_ID}.{DATASET_ID}.workflow_docrag_embedded`
  GROUP BY dims
""").to_dataframe()
print(f'All {verify.iloc[0]["chunks"]} chunks embedded ({verify.iloc[0]["dims"]} dimensions)')
```

---
## Step 3 — Retrieve and generate (RAG)

Run the full RAG loop in a single SQL statement:
1. Embed the user question with `task_type => 'RETRIEVAL_QUERY'` (`text-embedding-005`)
2. Retrieve the top-`k` closest chunks with `VECTOR_SEARCH(..., distance_type => 'COSINE')`, carrying `uri`, `chunk_id`, `start_page`, and `end_page`
3. Format each chunk header with its document name, chunk number, and page span (`[doc | chunk N | pages S-E]`) and pass the assembled context to `AI.GENERATE` (`endpoint => 'gemini-2.5-flash'`) so the answer cites exact page provenance

```python
user_question = 'What is the total amount due on the invoice from Nexus Innovations Group?'

query = f"""
WITH retrieved AS (
  SELECT
    base.uri,
    base.chunk_id,
    base.start_page,
    base.end_page,
    base.content,
    distance
  FROM VECTOR_SEARCH(
    TABLE `{PROJECT_ID}.{DATASET_ID}.workflow_docrag_embedded`,
    'embedding',
    query_value => (AI.EMBED(
      content => '{user_question}',
      endpoint => 'text-embedding-005',
      task_type => 'RETRIEVAL_QUERY'
    )).result,
    top_k => 3,
    distance_type => 'COSINE'
  )
),
context AS (
  SELECT STRING_AGG(
    CONCAT(
      '[', REGEXP_EXTRACT(uri, r'[^/]+$'),
      ' | chunk ', CAST(chunk_id AS STRING),
      ' | pages ', CAST(start_page AS STRING), '-', CAST(end_page AS STRING), '] ',
      content
    ),
    '\\n\\n'
    ORDER BY distance
  ) AS docs
  FROM retrieved
)
SELECT (AI.GENERATE(
  CONCAT(
    'You are a financial document analyst. Answer the user question using ONLY the provided document chunks. ',
    'Include exact invoice numbers, amounts, due dates, and cite each source as [filename, chunk N, pages S-E]. ',
    'If multiple matching invoices exist, report each one clearly.\\n\\n',
    'Document chunks:\\n', c.docs,
    '\\n\\nUser question: {user_question}'
  ),
  endpoint => 'gemini-2.5-flash'
)).result AS answer
FROM context c
"""
df = client.query(query).to_dataframe()
print(f'Question: {user_question}\n')
print(df.iloc[0]['answer'])
```

### View the retrieved chunks

Inspect the exact chunks and cosine distances `VECTOR_SEARCH` passed into the prompt above (lower cosine distance means higher semantic similarity).

```python
query = f"""
SELECT
  REGEXP_EXTRACT(base.uri, r'[^/]+$') AS document,
  base.chunk_id,
  base.start_page,
  base.end_page,
  ROUND(distance, 4) AS cosine_distance,
  LEFT(REPLACE(base.content, '\\n', ' '), 160) AS content_preview
FROM VECTOR_SEARCH(
  TABLE `{PROJECT_ID}.{DATASET_ID}.workflow_docrag_embedded`,
  'embedding',
  query_value => (AI.EMBED(
    content => '{user_question}',
    endpoint => 'text-embedding-005',
    task_type => 'RETRIEVAL_QUERY'
  )).result,
  top_k => 3,
  distance_type => 'COSINE'
)
ORDER BY distance
"""
client.query(query).to_dataframe()
```

### Batch RAG: answer multiple questions across invoices and multi-page policy

`VECTOR_SEARCH` accepts a **query table** so BigQuery retrieves top-`k` chunks for an entire batch of questions in one pass. Notice how the first question pulls multi-page chunks (`chunk_id > 1`, `pages 2-3`) from `ap_vendor_policy.pdf`, while the invoice questions pull specific single-page invoices — and when a document genuinely omits a field, grounded prompting reports that cleanly instead of guessing.

```python
query = f"""
WITH questions AS (
  SELECT question_id, question
  FROM UNNEST([
    STRUCT(1 AS question_id, 'Under the Accounts Payable policy, what approval is required for invoices over $25,000 and how quickly must billing discrepancies be reported?' AS question),
    STRUCT(2 AS question_id, 'What are the payment terms on invoice INV-2024-0013, and what is the standard fallback term in the Accounts Payable policy?' AS question),
    STRUCT(3 AS question_id, 'List the invoices due in November 2023 from the retrieved chunks with their invoice numbers and total amounts.' AS question)
  ])
),
retrieved AS (
  SELECT
    query.question_id,
    query.question AS user_question,
    base.uri,
    base.chunk_id,
    base.start_page,
    base.end_page,
    base.content,
    distance
  FROM VECTOR_SEARCH(
    TABLE `{PROJECT_ID}.{DATASET_ID}.workflow_docrag_embedded`,
    'embedding',
    (SELECT
       question_id,
       question,
       (AI.EMBED(
         content => question,
         endpoint => 'text-embedding-005',
         task_type => 'RETRIEVAL_QUERY'
       )).result AS embedding
     FROM questions),
    top_k => 4,
    distance_type => 'COSINE'
  )
),
context_per_question AS (
  SELECT
    question_id,
    user_question,
    STRING_AGG(
      CONCAT(
        '[', REGEXP_EXTRACT(uri, r'[^/]+$'),
        ' | chunk ', CAST(chunk_id AS STRING),
        ' | pages ', CAST(start_page AS STRING), '-', CAST(end_page AS STRING), '] ',
        content
      ),
      '\\n\\n'
      ORDER BY distance
    ) AS context
  FROM retrieved
  GROUP BY question_id, user_question
)
SELECT
  question_id,
  user_question,
  (AI.GENERATE(
    CONCAT(
      'Answer the question concisely based ONLY on the provided document chunks. ',
      'Cite every fact with [filename, chunk N, pages S-E]. ',
      'If a specific field is absent from an invoice, state that explicitly.\\n\\n',
      'Chunks:\\n', context,
      '\\n\\nQuestion: ', user_question
    ),
    endpoint => 'gemini-2.5-flash'
  )).result AS answer
FROM context_per_question
ORDER BY question_id
"""
df = client.query(query).to_dataframe()
for _, row in df.iterrows():
    print(f'Q{row["question_id"]}: {row["user_question"]}')
    print(f'A:  {row["answer"]}\n')
```

---
## Step 4 — RAG vs direct generation

Compare the exact same question answered **without** retrieved chunks vs **with** `AI.CHUNK_DOCUMENT` + `VECTOR_SEARCH` context on `gemini-2.5-flash`. Without retrieved evidence, the model cannot know private invoice totals or reference numbers; with RAG, every amount is anchored to a specific PDF chunk and page range.

```python
comparison_question = 'What is the total amount due on the invoice from Nexus Innovations Group, and whose sign-off does our AP policy require for the larger Nexus invoice?'

query = f"""
WITH no_rag AS (
  SELECT (AI.GENERATE(
    CONCAT(
      'Answer this question. If you do not have access to the private documents, say so clearly. ',
      'Question: {comparison_question}'
    ),
    endpoint => 'gemini-2.5-flash'
  )).result AS answer
),
rag_context AS (
  SELECT STRING_AGG(
    CONCAT(
      '[', REGEXP_EXTRACT(base.uri, r'[^/]+$'),
      ' | chunk ', CAST(base.chunk_id AS STRING),
      ' | pages ', CAST(base.start_page AS STRING), '-', CAST(base.end_page AS STRING), '] ',
      base.content
    ),
    '\\n\\n'
    ORDER BY distance
  ) AS docs
  FROM VECTOR_SEARCH(
    TABLE `{PROJECT_ID}.{DATASET_ID}.workflow_docrag_embedded`,
    'embedding',
    query_value => (AI.EMBED(
      content => '{comparison_question}',
      endpoint => 'text-embedding-005',
      task_type => 'RETRIEVAL_QUERY'
    )).result,
    top_k => 5,
    distance_type => 'COSINE'
  )
),
with_rag AS (
  SELECT (AI.GENERATE(
    CONCAT(
      'Answer this question based ONLY on the provided document chunks. ',
      'Include specific invoice numbers, dollar amounts, approval tier rules, and [filename, chunk N, pages S-E] citations.\\n\\n',
      'Document chunks:\\n', docs,
      '\\n\\nQuestion: {comparison_question}'
    ),
    endpoint => 'gemini-2.5-flash'
  )).result AS answer
  FROM rag_context
)
SELECT 1 AS sort_order, 'Without RAG (direct AI.GENERATE)' AS method, answer FROM no_rag
UNION ALL
SELECT 2 AS sort_order, 'With Document RAG (AI.CHUNK_DOCUMENT + VECTOR_SEARCH)' AS method, answer FROM with_rag
ORDER BY sort_order
"""
df = client.query(query).to_dataframe()
for _, row in df.iterrows():
    print(f'=== {row["method"]} ===')
    print(f'{row["answer"]}\n')
```

**Without RAG**, `gemini-2.5-flash` rightly declines because private vendor invoices and internal AP approval policies do not exist in pretraining weights. **With Document RAG**, a single SQL query combines facts across multiple PDFs — retrieving both Nexus Innovations Group invoices (`invoice_003.pdf` and `invoice_001.pdf`) and the relevant approval-threshold chunk from `ap_vendor_policy.pdf` — and cites the exact `chunk_id` and `start_page`–`end_page` for each claim.

### Choosing a document QA pattern in BigQuery

| Dimension | Direct `AI.GENERATE` (text only) | Multimodal `AI.GENERATE` (`ObjectRef` input) | Document RAG (`AI.CHUNK_DOCUMENT` + `VECTOR_SEARCH`) |
|-----------|----------------------------------|----------------------------------------------|------------------------------------------------------|
| **Setup** | None | Object table or `OBJ.MAKE_REF` | Object table / `OBJ.MAKE_REF` + persisted chunk & embedding tables |
| **Per-question cost** | Lowest (prompt tokens only) | Re-reads full PDF bytes on every prompt | Embeds query once + passes only top-`k` chunks |
| **Multi-document search** | Cannot access private files | Must already know which row/file to inspect | Searches across hundreds or thousands of PDFs, DOCX, PPTX, XLSX, and HTML files |
| **Citations** | None | File-level `uri` only | Exact `uri`, `chunk_id`, `start_page`, and `end_page` |
| **Best for** | General world knowledge or text already inline in a SQL column | One-pass field extraction or visual inspection on a known document (see `workflows/document_intelligence` (Document Intelligence)) | Reusable question answering and policy/invoice search across a growing document corpus |
