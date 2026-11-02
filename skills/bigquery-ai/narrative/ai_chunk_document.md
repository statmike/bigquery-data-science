> **Source (`statmike/bigquery-data-science`):** **Notebook:** [`bigquery-ai/functions/ai_chunk_document/ai_chunk_document.ipynb`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ai/functions/ai_chunk_document/ai_chunk_document.ipynb) · **SQL:** [`bigquery-ai/functions/ai_chunk_document/ai_chunk_document.sql`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ai/functions/ai_chunk_document/ai_chunk_document.sql)

# AI.CHUNK_DOCUMENT — BigQuery AI Functions

`AI.CHUNK_DOCUMENT` splits unstructured documents in Cloud Storage (PDF, HTML, DOCX, PPTX, XLSX, and XLSM) into layout-aware, page-attributed text chunks directly in BigQuery SQL — with zero `CREATE MODEL` DDL and zero manual Document AI processor setup. On the first call in a project, BigQuery automatically provisions and reuses a shared Document AI Layout Parser processor (`bq-created-layout-parser`, zero idle fee) that respects headings, paragraphs, lists, and tables and prepends ancestor section headings so each chunk carries its structural context into RAG and search.

**When to use it:**
- You are preparing PDFs, HTML pages, Word docs, slide decks, or spreadsheets for `functions/ai_embed` (`AI.EMBED`) + `functions/vector_search` (`VECTOR_SEARCH`) / `functions/ai_search` (`AI.SEARCH`)
- You want typed `chunk_id`, `start_page`, `end_page`, `content`, and `status` columns straight out of a table-valued function instead of unpacking nested Document AI JSON
- You want zero model or processor lifecycle management (`CREATE MODEL` is not required)

**Alternatives:**
- `functions/ml_process_document` (`ML.PROCESS_DOCUMENT`) — Pre-trained specialized Document AI processors (Invoice Parser, Expense Parser, Form Parser) via `CREATE MODEL ... REMOTE WITH CONNECTION ... OPTIONS(REMOTE_SERVICE_TYPE = 'CLOUD_AI_DOCUMENT_V1')` when you need normalized domain entities (`total_amount`, `due_date`, `line_items`) rather than text chunks
- `functions/ai_generate` (`AI.GENERATE`) / `functions/ai_generate_table` (`AI.GENERATE_TABLE`) — Pass `ObjectRef` documents directly to Gemini when you want a single-pass summary, Q&A answer, or custom `output_schema` extraction over a whole document without chunking first
- `functions/ai_parse_document` (`AI.PARSE_DOCUMENT`) *(retired 2026-06-01)* — Preview predecessor superseded by GA `AI.CHUNK_DOCUMENT`

**Featured in:** `workflows/document_rag` (Document RAG)

**References:** `reference/document-processing.md#aichunk_document` (Document Processing reference) | `RESOURCES.md` (Full syntax reference) | [Official documentation](https://docs.cloud.google.com/bigquery/docs/reference/standard-sql/bigqueryml-syntax-ai-chunk-document) | `setup` (Setup guide)

---
## Setup

Set your project and location, enable the Document AI API, configure the shared Cloud resource connection, and stage a compact multi-format document set in Cloud Storage.

> **How authentication and processor provisioning work:**
> - **Auto-provisioned Layout Parser:** `AI.CHUNK_DOCUMENT` requires `documentai.googleapis.com`. The first call in a project automatically creates a single Document AI Layout Parser processor named `bq-created-layout-parser` (`LAYOUT_PARSER_PROCESSOR`) and reuses it on every subsequent call at zero idle cost (`$10` per `1,000` processed pages).
> - **End-user credentials (EUC) vs Cloud resource connection:** Direct `'gs://...'` URI literals and 1-argument `OBJ.MAKE_REF(uri)` run under the caller's own IAM roles by default; Object Tables, 2-argument `OBJ.MAKE_REF(uri, connection_id)`, and explicit `connection_id => ...` calls delegate Storage and Document AI access to the connection's service account.
> - **Regional availability:** Supported in `US` and `EU` multi-regions and in US/EU single regions **except `europe-west2` (London) and `europe-west6` (Zürich)**.
> - **VPC Service Controls:** Delegated `ObjectRef` inputs (`connection_id`, Object Tables, and `OBJ.MAKE_REF(uri, connection_id)`) mint signed HTTPS URLs and fail inside VPC-SC perimeters (`HTTP links are not supported for requests restricted by VPCSC`). Inside VPC-SC, authenticate with EUC (`'gs://...'` literal or 1-argument `OBJ.MAKE_REF(uri)`).

```python
import os
from pathlib import Path
import google.auth

PROJECT_ID = 'your-gcp-project-id'  # <-- Replace with your project ID (or leave to auto-detect)
if PROJECT_ID == 'your-gcp-project-id':
    for _p in [Path.cwd(), *Path.cwd().parents]:
        if (_p / '.env').is_file():
            for _k, _v in (
                l.split('=', 1)
                for l in (_p / '.env').read_text().splitlines()
                if '=' in l and not l.strip().startswith('#')
            ):
                os.environ.setdefault(_k.strip(), _v.strip().strip('\'"'))
            break
    PROJECT_ID = os.environ.get('GOOGLE_CLOUD_PROJECT') or google.auth.default()[1] or 'your-gcp-project-id'

LOCATION = 'US'                     # Region for dataset, connection, and bucket
DATASET_ID = 'bq_ai_functions'      # Shared dataset across all notebooks in this project
CONNECTION_ID = 'bq_ai_functions'   # Shared Cloud resource connection
BUCKET = PROJECT_ID                 # GCS bucket (same name as project — see setup/)
GCS_PREFIX = 'bq_ai_functions/ai_chunk_document'
```

### Environment

> **Already set up the project environment?** The cell below is a no-op — packages are already in your kernel. See the `setup` (Setup Reference) for details.
>
> **Running standalone** (Colab, Colab Enterprise, Vertex AI Workbench)? The cell below installs required packages into your current kernel.

```python
from google.cloud import bigquery
import pandas as pd

client = bigquery.Client(project=PROJECT_ID)
pd.set_option('display.max_colwidth', 140)

dataset_ref = bigquery.DatasetReference(PROJECT_ID, DATASET_ID)
dataset = bigquery.Dataset(dataset_ref)
dataset.location = LOCATION
client.create_dataset(dataset, exists_ok=True)
print(f'Dataset {PROJECT_ID}.{DATASET_ID} ready')

%load_ext bigquery_magics
```

### APIs, connection, and IAM roles

`AI.CHUNK_DOCUMENT` checks Document AI permissions differently depending on whether the project's `bq-created-layout-parser` processor has already been auto-created:

| Principal | Role | Why it is needed |
|---|---|---|
| Query caller (EUC or connection path) | `roles/bigquery.jobUser` | Run BigQuery queries in the project |
| Query caller (connection path) | `roles/bigquery.connectionUser` | Use the Cloud resource connection |
| EUC caller *or* Connection SA | `roles/storage.objectViewer` | Read source documents in Cloud Storage |
| EUC caller *or* Connection SA | `roles/documentai.editor` *(first call)* / `roles/documentai.viewer` *(thereafter)* | Auto-create `bq-created-layout-parser` on the very first call in the project; invoke it on subsequent calls |
| Connection SA | `roles/serviceusage.serviceUsageConsumer` | Consume Cloud AI APIs through the connection |
| Connection SA *(Example 6 only)* | `roles/aiplatform.user` | Call Gemini via `AI.GENERATE` in the side-by-side comparison |

```python
import json as _json
import re as _re
import subprocess as _sp
from google.cloud import storage

REQUIRED_APIS = [
    'bigquery.googleapis.com',
    'bigqueryconnection.googleapis.com',
    'documentai.googleapis.com',
    'aiplatform.googleapis.com',
    'storage.googleapis.com',
]

enabled = set(
    _sp.run(
        ['gcloud', 'services', 'list', '--enabled', '--format=value(config.name)', f'--project={PROJECT_ID}'],
        capture_output=True, text=True, check=True,
    ).stdout.split()
)
missing_apis = [api for api in REQUIRED_APIS if api not in enabled]
for api in missing_apis:
    _sp.run(['gcloud', 'services', 'enable', api, f'--project={PROJECT_ID}'], capture_output=True, text=True, check=True)
print(f'APIs ready ({len(REQUIRED_APIS)} checked, {len(missing_apis)} enabled now)')

# Create Cloud resource connection idempotently
_sp.run(
    ['bq', 'mk', '--connection', '--location', LOCATION, '--connection_type', 'CLOUD_RESOURCE', '--project_id', PROJECT_ID, CONNECTION_ID],
    capture_output=True, text=True,
)
conn_info = _sp.run(
    ['bq', 'show', '--connection', '--format=json', '--project_id', PROJECT_ID, '--location', LOCATION, CONNECTION_ID],
    capture_output=True, text=True, check=True,
)
sa = _json.loads(conn_info.stdout)['cloudResource']['serviceAccountId']
sa_display = _re.sub(r'bqcx-\d+-', 'bqcx-000000000000-', sa)
print(f'Connection service account: {sa_display}')

REQUIRED_ROLES = [
    'roles/serviceusage.serviceUsageConsumer',
    'roles/bigquery.connectionUser',
    'roles/storage.objectViewer',
    'roles/documentai.editor',   # editor covers first-run auto-creation of bq-created-layout-parser; viewer suffices thereafter
    'roles/aiplatform.user',     # used only for the AI.GENERATE comparison in Example 6
]

policy_out = _sp.run(
    [
        'gcloud', 'projects', 'get-iam-policy', PROJECT_ID,
        '--flatten=bindings[].members',
        f'--filter=bindings.members:{sa}',
        '--format=value(bindings.role)',
    ],
    capture_output=True, text=True, check=True,
)
held_roles = set(policy_out.stdout.split())
missing_roles = [role for role in REQUIRED_ROLES if role not in held_roles]
for role in missing_roles:
    _sp.run(
        [
            'gcloud', 'projects', 'add-iam-policy-binding', PROJECT_ID,
            f'--member=serviceAccount:{sa}', f'--role={role}', '--condition=None', '--quiet',
        ],
        capture_output=True, text=True, check=True,
    )
print(f'Already held: {", ".join(sorted(set(REQUIRED_ROLES) & held_roles)) or "none"}')
print(f'Granted now:  {", ".join(missing_roles) or "none"}')

# Ensure GCS bucket exists
gcs_client = storage.Client(project=PROJECT_ID)
bucket = gcs_client.bucket(BUCKET)
if not bucket.exists():
    bucket = gcs_client.create_bucket(BUCKET, location=LOCATION)
print(f'Bucket gs://{BUCKET} ready')
```

### Stage sample documents and create an Object Table

To test multi-page spans, chunk-size granularity, multi-format parsing, and per-row error reporting without external dependencies, we stage six small files under `gs://{BUCKET}/bq_ai_functions/ai_chunk_document/` (and delete all six at the end of the notebook):

1. `docs/handbook_multipage.pdf` — 4-page *Cloud Operations Runbook* rendered in memory with `weasyprint` (headings, an SLO table, a triage checklist, and explicit page breaks)
2. `docs/invoice_001.pdf` — Synthetic 1-page service invoice from `data/documents` (`data/documents/invoices/`) (with an in-memory fallback when running standalone in Colab), used in Example 6 to compare `AI.CHUNK_DOCUMENT`, `AI.GENERATE`, and `ML.PROCESS_DOCUMENT`
3. `formats/release_notes.html` — Structured HTML release notes (`text/html`)
4. `formats/vendor_policy.docx` — Word document (`application/vnd.openxmlformats-officedocument.wordprocessingml.document`)
5. `formats/slo_matrix.xlsx` — Excel spreadsheet (`application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`)
6. `unsupported/plain_note.txt` — Plain-text file (`text/plain`) intentionally staged to trigger a per-row `status` error without aborting the query

We also create an Object Table (`bq_ai_functions.ai_chunk_document_docs`) over `docs/*.pdf` so Example 3 can compare all three input shapes side by side.

```python
import io
import zipfile
from weasyprint import HTML

def build_minimal_docx(title: str, paragraphs: list[str]) -> bytes:
    """Build a minimal ECMA-376 .docx archive using only the Python standard library."""
    body = f'<w:p><w:r><w:t>{title}</w:t></w:r></w:p>' + ''.join(
        f'<w:p><w:r><w:t>{p}</w:t></w:r></w:p>' for p in paragraphs
    )
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.writestr('[Content_Types].xml', '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
</Types>''')
        zf.writestr('_rels/.rels', '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>''')
        zf.writestr('word/document.xml', f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body>{body}<w:sectPr/></w:body>
</w:document>''')
    return buf.getvalue()

def build_minimal_xlsx(rows: list[list[str]]) -> bytes:
    """Build a minimal ECMA-376 .xlsx workbook using only the Python standard library."""
    sheet_rows = []
    for r_idx, row in enumerate(rows, start=1):
        cells = ''.join(
            f'<c r="{chr(64 + c_idx)}{r_idx}" t="inlineStr"><is><t>{val}</t></is></c>'
            for c_idx, val in enumerate(row, start=1)
        )
        sheet_rows.append(f'<row r="{r_idx}">{cells}</row>')
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.writestr('[Content_Types].xml', '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
  <Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
  <Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>
</Types>''')
        zf.writestr('_rels/.rels', '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
</Relationships>''')
        zf.writestr('xl/workbook.xml', '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <sheets><sheet name="SLO Matrix" sheetId="1" r:id="rId1"/></sheets>
</workbook>''')
        zf.writestr('xl/_rels/workbook.xml.rels', '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
</Relationships>''')
        zf.writestr('xl/styles.xml', '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <fonts count="1"><font><sz val="11"/><name val="Calibri"/></font></fonts>
  <fills count="1"><fill><patternFill patternType="none"/></fill></fills>
  <borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders>
  <cellXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellXfs>
</styleSheet>''')
        zf.writestr('xl/worksheets/sheet1.xml', f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <sheetData>{''.join(sheet_rows)}</sheetData>
</worksheet>''')
    return buf.getvalue()

handbook_html = (
    '<!DOCTYPE html><html><head><style>'
    '@page { size: letter; margin: 1in; } .page-break { page-break-before: always; }'
    'table { border-collapse: collapse; width: 100%; } th, td { border: 1px solid #444; padding: 6px; text-align: left; }'
    '</style></head><body>'
    '<h1>Cloud Operations Runbook</h1>'
    '<h2>1. Architecture Overview</h2>'
    '<p>This runbook defines operational procedures, escalation tiers, and recovery objectives for regional data pipelines.</p>'
    '<p>' + ('Operational telemetry streams continuously into analytical tables for automated anomaly detection and alerting. ' * 18) + '</p>'
    '<h2 class="page-break">2. Service Level Objectives</h2>'
    '<p>Every production pipeline enforces explicit latency, freshness, and completeness targets reviewed weekly.</p>'
    '<table><tr><th>Tier</th><th>Freshness Target</th><th>Availability SLO</th><th>Escalation Window</th></tr>'
    '<tr><td>Tier 1 (Critical)</td><td>15 minutes</td><td>99.95%</td><td>5 minutes</td></tr>'
    '<tr><td>Tier 2 (Standard)</td><td>2 hours</td><td>99.50%</td><td>30 minutes</td></tr>'
    '<tr><td>Tier 3 (Batch)</td><td>24 hours</td><td>99.00%</td><td>Next business day</td></tr></table>'
    '<p>' + ('Automated freshness monitors compare watermark timestamps against expected schedule intervals every five minutes. ' * 15) + '</p>'
    '<h2 class="page-break">3. Incident Triage Checklist</h2>'
    '<h3>3.1 Ingestion Failures</h3>'
    '<ul><li>Verify upstream storage bucket permissions and service account IAM bindings.</li>'
    '<li>Inspect dead-letter rows and per-file status messages before replaying failed batches.</li>'
    '<li>Confirm schema evolution compatibility for newly added nested fields.</li></ul>'
    '<p>' + ('Triage responders record incident timelines, root causes, and remediation queries in the shared postmortem log. ' * 16) + '</p>'
    '<h2 class="page-break">4. Disaster Recovery and Failover</h2>'
    '<h3>4.1 Cross-Region Promotion</h3>'
    '<p>When a primary region experiences sustained degradation, promote replica datasets and re-point scheduled orchestrators.</p>'
    '<p>' + ('Quarterly failover drills validate recovery point objectives and verify downstream dashboard continuity end to end. ' * 16) + '</p>'
    '</body></html>'
)
handbook_pdf_bytes = HTML(string=handbook_html).write_pdf()

local_invoice = Path('../../data/documents/invoices/invoice_001.pdf')
if not local_invoice.exists():
    local_invoice = Path('bigquery-ai/data/documents/invoices/invoice_001.pdf')
if local_invoice.exists():
    invoice_pdf_bytes = local_invoice.read_bytes()
else:
    invoice_pdf_bytes = HTML(string=(
        '<html><body><h1>INVOICE INV-2024-0013</h1><p>Supplier: Nexus Innovations Group</p>'
        '<p>Date: 2024-02-15 | Due: 2024-03-16</p>'
        '<table><tr><th>Description</th><th>Qty</th><th>Unit Price</th><th>Amount</th></tr>'
        '<tr><td>Cloud Architecture Advisory</td><td>40</td><td>$225.00</td><td>$9,000.00</td></tr>'
        '<tr><td>Security Readiness Audit</td><td>1</td><td>$1,067.25</td><td>$1,067.25</td></tr></table>'
        '<p><strong>Total Due: $10,067.25</strong></p></body></html>'
    )).write_pdf()

release_html_bytes = (
    '<!DOCTYPE html><html><body>'
    '<h1>Platform Release Notes v4.2</h1>'
    '<h2>Highlights</h2>'
    '<p>Introduced automated layout-aware document chunking and hybrid vector search indexing.</p>'
    '<h2>Upgrade Notes</h2>'
    '<ul><li>Filter chunk outputs on empty-string status before embedding.</li>'
    '<li>Pin foundation model endpoints in scheduled SQL pipelines.</li></ul>'
    '</body></html>'
).encode('utf-8')

docx_bytes = build_minimal_docx(
    'Vendor Security Onboarding Policy',
    [
        '1. All third-party data processors must complete an annual security review before production onboarding.',
        '2. Regional storage buckets must enforce uniform bucket-level access and least-privilege IAM roles.',
    ],
)
xlsx_bytes = build_minimal_xlsx([
    ['Service', 'Owner', 'Availability_SLO', 'RPO_Minutes'],
    ['Ingestion Gateway', 'Data Platform', '99.95%', '15'],
    ['Feature Store Sync', 'ML Infrastructure', '99.90%', '60'],
])
txt_bytes = b'Plain text note: text/plain is intentionally unsupported by AI.CHUNK_DOCUMENT.'

staged_payloads = [
    (f'{GCS_PREFIX}/docs/handbook_multipage.pdf', handbook_pdf_bytes, 'application/pdf'),
    (f'{GCS_PREFIX}/docs/invoice_001.pdf', invoice_pdf_bytes, 'application/pdf'),
    (f'{GCS_PREFIX}/formats/release_notes.html', release_html_bytes, 'text/html'),
    (
        f'{GCS_PREFIX}/formats/vendor_policy.docx',
        docx_bytes,
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    ),
    (
        f'{GCS_PREFIX}/formats/slo_matrix.xlsx',
        xlsx_bytes,
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    ),
    (f'{GCS_PREFIX}/unsupported/plain_note.txt', txt_bytes, 'text/plain'),
]

for blob_name, raw_bytes, mime_type in staged_payloads:
    bucket.blob(blob_name).upload_from_string(raw_bytes, content_type=mime_type)

client.query(f"""
CREATE OR REPLACE EXTERNAL TABLE `{PROJECT_ID}.{DATASET_ID}.ai_chunk_document_docs`
WITH CONNECTION `{PROJECT_ID}.{LOCATION}.{CONNECTION_ID}`
OPTIONS (
  object_metadata = 'SIMPLE',
  uris = ['gs://{BUCKET}/{GCS_PREFIX}/docs/*.pdf']
)
""").result()

print(f'Staged {len(staged_payloads)} files under gs://{BUCKET}/{GCS_PREFIX}/')
print(f'Object table {DATASET_ID}.ai_chunk_document_docs ready')
```

---
## Examples — Python Client

`AI.CHUNK_DOCUMENT` is a table-valued function (TVF) used in a SQL `FROM` clause:

```sql
AI.CHUNK_DOCUMENT(
  { 'STORAGE_URI' | TABLE input_table | (query_statement) }
  [, connection_id => 'CONNECTION_ID']
  [, chunk_size => CHUNK_SIZE]
)
```

| Argument | Type | Default | Notes |
|---|---|---|---|
| First positional input | `'gs://...'` URI/wildcard, `TABLE object_table`, or `(SELECT ... AS ref)` | *(required)* | URI literals and Object Tables emit **13 columns** (5 chunk + 8 object metadata); `(query_statement)` emits **`5 + passthrough` columns** |
| `connection_id` | `STRING` | Caller EUC (or Object Table connection) | Format `'LOCATION.CONNECTION_ID'` or `'PROJECT_ID.LOCATION.CONNECTION_ID'` |
| `chunk_size` | `INT64` | `1000` | Target chunk size in **tokens**, bounded to **`1..2000`**. Top-level named `INT64` argument — **not** an `options => JSON` string |

### Example 1: Simplest starter call — URI literal & all 13 output columns

Pass a `'gs://...'` URI (or wildcard such as `'gs://.../docs/*.pdf'`) directly to `AI.CHUNK_DOCUMENT`. With no `connection_id` and no `chunk_size`, BigQuery authenticates with your end-user credentials (EUC), uses the default `chunk_size => 1000` tokens, and returns **13 columns**:

- **5 chunk columns:** `chunk_id` (`INT64`, 1-based per document), `start_page` (`INT64`, 1-based), `end_page` (`INT64`, 1-based), `content` (`STRING`), and `status` (`STRING`, `''` on success)
- **8 object metadata columns:** `uri`, `generation`, `content_type`, `size`, `md5_hash`, `updated`, `metadata`, and `ref`

Notice how Layout Parser formats headings (`#`, `##`) and HTML/PDF tables into clean Markdown-style text so downstream embedding models preserve table row-and-column structure.

```python
query = f"""
SELECT *
FROM AI.CHUNK_DOCUMENT('gs://{BUCKET}/{GCS_PREFIX}/docs/handbook_multipage.pdf')
ORDER BY chunk_id
"""
df_ex1 = client.query(query).to_dataframe()
print(f'Returned {len(df_ex1)} chunk(s) across {len(df_ex1.columns)} columns:')
print(list(df_ex1.columns))
df_ex1[['chunk_id', 'start_page', 'end_page', 'status', 'content_type', 'size', 'content']]
```

### Example 2: Tuning chunk granularity with `chunk_size`

`chunk_size` sets the target upper bound in tokens (`1..2000`, default `1000`). Below we compare `chunk_size => 150` against `chunk_size => 1000` on the same 4-page runbook PDF.

> **Why can a chunk on page 3 report `start_page = 1` and `end_page = 3`?**
> Document AI's Layout Parser automatically prepends **ancestor headings** (such as the top-level `# Cloud Operations Runbook` `<h1>` title from page 1) to nested sections on later pages so every chunk remains self-contained when retrieved in isolation. Because `start_page` and `end_page` track the earliest and latest page contributing tokens to that chunk, prepended top-level headings naturally produce wider page spans (`1..3` or `1..4`) on deeper sections!

```python
summary_query = f"""
WITH
  fine AS (
    SELECT 150 AS target_tokens, *
    FROM AI.CHUNK_DOCUMENT(
      'gs://{BUCKET}/{GCS_PREFIX}/docs/handbook_multipage.pdf',
      chunk_size => 150
    )
    WHERE status = ''
  ),
  coarse AS (
    SELECT 1000 AS target_tokens, *
    FROM AI.CHUNK_DOCUMENT(
      'gs://{BUCKET}/{GCS_PREFIX}/docs/handbook_multipage.pdf',
      chunk_size => 1000
    )
    WHERE status = ''
  ),
  combined AS (
    SELECT * FROM fine
    UNION ALL
    SELECT * FROM coarse
  )
SELECT
  target_tokens,
  COUNT(*) AS chunk_count,
  MIN(CHAR_LENGTH(content)) AS min_chars,
  CAST(ROUND(AVG(CHAR_LENGTH(content))) AS INT64) AS avg_chars,
  MAX(CHAR_LENGTH(content)) AS max_chars,
  COUNT(DISTINCT FORMAT('%d-%d', start_page, end_page)) AS distinct_page_spans
FROM combined
GROUP BY target_tokens
ORDER BY target_tokens
"""
display(client.query(summary_query).to_dataframe())

detail_query = f"""
SELECT
  chunk_id,
  start_page,
  end_page,
  CHAR_LENGTH(content) AS char_len,
  SUBSTR(REPLACE(content, '\\n', ' ⏎ '), 1, 120) AS content_preview
FROM AI.CHUNK_DOCUMENT(
  'gs://{BUCKET}/{GCS_PREFIX}/docs/handbook_multipage.pdf',
  chunk_size => 150
)
WHERE status = ''
ORDER BY chunk_id
"""
client.query(detail_query).to_dataframe()
```

### Example 3: All 3 input shapes — and the output-column trap on subqueries

`AI.CHUNK_DOCUMENT` accepts three input shapes as its first argument, and two live behaviors differ from what a quick read of the reference page suggests:

1. **Shape A — `'gs://...'` URI or wildcard literal (`13` output columns):** Uses EUC by default, **and also accepts `connection_id => ...`** (the reference page says URI literals must use EUC, but delegated connections work on URI literals and wildcards too).
2. **Shape B — `TABLE object_table` (`13` output columns):** Reads an Object Table using its attached connection automatically.
3. **Shape C — `(SELECT ... AS ref ...)` subquery (`5 + passthrough` columns ONLY):** Accepts any query producing an `ObjectRef` column named `ref` (from `OBJ.MAKE_REF` or `OBJ.LIST`). **Watch the output schema:** unlike Shapes A and B, Shape C **does not emit a top-level `uri`, `size`, or `content_type` column** unless your subquery explicitly selects them! Instead, it preserves your subquery's passthrough columns (such as `doc_id` and `doc_category`) alongside `ref`, so you read the URI via `ref.uri`.

```python
conn_arg = f'{PROJECT_ID}.{LOCATION}.{CONNECTION_ID}'

# Shape A: URI wildcard literal WITH connection_id (proving delegated auth works on URI literals too)
df_shape_a = client.query(f"""
SELECT *
FROM AI.CHUNK_DOCUMENT(
  'gs://{BUCKET}/{GCS_PREFIX}/docs/*.pdf',
  connection_id => '{conn_arg}',
  chunk_size => 400
)
WHERE status = ''
ORDER BY uri, chunk_id
""").to_dataframe()

# Shape B: Object Table
df_shape_b = client.query(f"""
SELECT *
FROM AI.CHUNK_DOCUMENT(
  TABLE `{PROJECT_ID}.{DATASET_ID}.ai_chunk_document_docs`,
  chunk_size => 400
)
WHERE status = ''
ORDER BY uri, chunk_id
""").to_dataframe()

# Shape C: Subquery with OBJ.MAKE_REF + custom passthrough metadata columns (doc_id, doc_category)
df_shape_c = client.query(f"""
SELECT
  doc_id,
  doc_category,
  ref.uri AS source_uri,
  chunk_id,
  start_page,
  end_page,
  CHAR_LENGTH(content) AS char_len
FROM AI.CHUNK_DOCUMENT(
  (
    SELECT
      doc_id,
      doc_category,
      OBJ.MAKE_REF(uri, '{conn_arg}') AS ref
    FROM UNNEST([
      STRUCT('DOC-RUNBOOK' AS doc_id, 'operations' AS doc_category, 'gs://{BUCKET}/{GCS_PREFIX}/docs/handbook_multipage.pdf' AS uri),
      STRUCT('DOC-INV-001' AS doc_id, 'finance' AS doc_category, 'gs://{BUCKET}/{GCS_PREFIX}/docs/invoice_001.pdf' AS uri)
    ])
  ),
  chunk_size => 400
)
WHERE status = ''
ORDER BY doc_id, chunk_id
""").to_dataframe()

# Inspect raw column list of Shape C (SELECT *)
df_shape_c_raw = client.query(f"""
SELECT *
FROM AI.CHUNK_DOCUMENT(
  (SELECT 'DOC-INV-001' AS doc_id, OBJ.MAKE_REF('gs://{BUCKET}/{GCS_PREFIX}/docs/invoice_001.pdf', '{conn_arg}') AS ref)
)
""").to_dataframe()

print(f'Shape A (URI wildcard + connection_id): {len(df_shape_a)} rows, {len(df_shape_a.columns)} cols -> top-level "uri" in cols: {"uri" in df_shape_a.columns}')
print(f'Shape B (TABLE object_table):           {len(df_shape_b)} rows, {len(df_shape_b.columns)} cols -> top-level "uri" in cols: {"uri" in df_shape_b.columns}')
print(f'Shape C (OBJ.MAKE_REF subquery):        {len(df_shape_c_raw.columns)} cols -> {list(df_shape_c_raw.columns)}')
df_shape_c
```

### Example 4: Supported formats, the 3-way `status` contract, and boundary errors

At GA, `AI.CHUNK_DOCUMENT` supports **PDF** (`.pdf`), **HTML** (`.html`), **Word** (`.docx`), **PowerPoint** (`.pptx`), and **Excel** (`.xlsx`, `.xlsm`). Per-document failures do **not** abort a batch query — instead, `status` has **three** distinct runtime states:

| Input outcome | `status` value | `chunk_id` & `content` |
|---|---|---|
| Valid document chunk | `''` *(empty string)* | Populated (`>= 1` and chunk text) |
| Unsupported MIME type (e.g., `.txt` `text/plain`) or >15-page/corrupt file | Non-empty error string (`'INVALID_ARGUMENT: ...'`) | `NULL` |
| Missing Cloud Storage object (`gs://.../does_not_exist.pdf`) | **`NULL`** | `NULL` |

> **Production filtering rule:** Always filter valid chunks with **`WHERE status = ''`**.
> - `WHERE status IS NULL` is a bug — it selects **missing-file failures**, not successes!
> - `WHERE status != ''` misses `NULL` rows when auditing errors — use **`WHERE status IS NULL OR status != ''`** to capture every failed document.

```python
status_contract_query = f"""
WITH MixedInputs AS (
  SELECT
    input_label,
    OBJ.MAKE_REF(uri, '{PROJECT_ID}.{LOCATION}.{CONNECTION_ID}') AS ref
  FROM UNNEST([
    STRUCT('1_html_valid'        AS input_label, 'gs://{BUCKET}/{GCS_PREFIX}/formats/release_notes.html'    AS uri),
    STRUCT('2_docx_valid'        AS input_label, 'gs://{BUCKET}/{GCS_PREFIX}/formats/vendor_policy.docx'    AS uri),
    STRUCT('3_xlsx_valid'        AS input_label, 'gs://{BUCKET}/{GCS_PREFIX}/formats/slo_matrix.xlsx'       AS uri),
    STRUCT('4_txt_unsupported'   AS input_label, 'gs://{BUCKET}/{GCS_PREFIX}/unsupported/plain_note.txt'    AS uri),
    STRUCT('5_pdf_missing_blob'  AS input_label, 'gs://{BUCKET}/{GCS_PREFIX}/docs/missing_document_404.pdf' AS uri)
  ])
)
SELECT
  input_label,
  chunk_id,
  start_page,
  end_page,
  CASE
    WHEN status = '' THEN 'valid_chunk'
    WHEN status != '' THEN 'processor_error'
    ELSE 'missing_blob_null_status'
  END AS row_outcome,
  IFNULL(status, '<NULL: missing GCS object>') AS status_display,
  status,
  SUBSTR(REPLACE(content, '\\n', ' ⏎ '), 1, 90) AS content_preview
FROM AI.CHUNK_DOCUMENT((SELECT * FROM MixedInputs), chunk_size => 500)
ORDER BY input_label, chunk_id
"""
df_status = client.query(status_contract_query).to_dataframe()
valid_count = int((df_status['status'] == '').sum())
failed_count = int((df_status['status'].isna() | (df_status['status'] != '')).sum())
print(f"Valid chunks (status == ''): {valid_count} | Failed rows (NULL or non-empty status): {failed_count}")
df_status[['input_label', 'chunk_id', 'start_page', 'end_page', 'row_outcome', 'status_display', 'content_preview']]
```

```python
from google.api_core.exceptions import GoogleAPIError

boundary_probes = [
    (
        'chunk_size => 0 (below 1)',
        f"SELECT * FROM AI.CHUNK_DOCUMENT('gs://{BUCKET}/{GCS_PREFIX}/docs/invoice_001.pdf', chunk_size => 0)",
    ),
    (
        'chunk_size => 2001 (above 2000)',
        f"SELECT * FROM AI.CHUNK_DOCUMENT('gs://{BUCKET}/{GCS_PREFIX}/docs/invoice_001.pdf', chunk_size => 2001)",
    ),
    (
        'Subquery missing ref column',
        f"SELECT * FROM AI.CHUNK_DOCUMENT((SELECT 'gs://{BUCKET}/{GCS_PREFIX}/docs/invoice_001.pdf' AS document_uri))",
    ),
    (
        'Top-level uri on subquery input',
        f"SELECT uri, content FROM AI.CHUNK_DOCUMENT((SELECT OBJ.MAKE_REF('gs://{BUCKET}/{GCS_PREFIX}/docs/invoice_001.pdf', '{PROJECT_ID}.{LOCATION}.{CONNECTION_ID}') AS ref))",
    ),
]

for label, bad_sql in boundary_probes:
    try:
        client.query(bad_sql).result()
    except GoogleAPIError as exc:
        msg = exc.message.splitlines()[0].replace(PROJECT_ID, 'your-gcp-project-id')
        print(f'[{label}]\n  -> {msg}\n')
```

### Example 5: Determinism check across uncached runs

Generative functions (`AI.GENERATE`, `AI.EVALUATE`, `ML.TRANSCRIBE`) can vary slightly across uncached runs. Because `AI.CHUNK_DOCUMENT` invokes the deterministic Document AI Layout Parser (`pretrained-layout-parser-v1.0-2024-06-03`), we can disable the BigQuery query cache (`use_query_cache=False`) across two consecutive calls and verify whether chunk boundaries, page spans, and extracted text match bit-for-bit.

```python
import hashlib

det_sql = f"""
SELECT chunk_id, start_page, end_page, content
FROM AI.CHUNK_DOCUMENT(
  'gs://{BUCKET}/{GCS_PREFIX}/docs/handbook_multipage.pdf',
  chunk_size => 200
)
WHERE status = ''
ORDER BY chunk_id
"""
nocache_cfg = bigquery.QueryJobConfig(use_query_cache=False)
run_1 = client.query(det_sql, job_config=nocache_cfg).to_dataframe()
run_2 = client.query(det_sql, job_config=nocache_cfg).to_dataframe()

def digest_df(df: pd.DataFrame) -> str:
    payload = '|'.join(
        f"{r.chunk_id}:{r.start_page}-{r.end_page}:{r.content}"
        for r in df.itertuples(index=False)
    )
    return hashlib.sha256(payload.encode('utf-8')).hexdigest()[:16]

h1, h2 = digest_df(run_1), digest_df(run_2)
print(f'Run 1: {len(run_1)} chunks | sha256[:16] = {h1}')
print(f'Run 2: {len(run_2)} chunks | sha256[:16] = {h2}')
print(f'Bit-for-bit identical across uncached runs: {run_1.equals(run_2)}')
```

### Example 6: Side-by-side — `AI.CHUNK_DOCUMENT` vs `AI.GENERATE` vs `ML.PROCESS_DOCUMENT`

BigQuery provides three distinct ways to work with documents in Cloud Storage. Here we run `AI.CHUNK_DOCUMENT` and multimodal `AI.GENERATE` (`endpoint => 'gemini-2.5-flash'`) on the exact same synthetic invoice (`invoice_001.pdf`), and compare both against `functions/ml_process_document` (`ML.PROCESS_DOCUMENT`):

- **`AI.CHUNK_DOCUMENT`** extracts deterministic, page-tracked Markdown text & tables ready to embed and index.
- **`AI.GENERATE` (with `output_schema`)** reads the `ObjectRef` directly with Gemini in a single pass to synthesize or extract custom typed fields (`vendor`, `invoice_number`, `total_due`, `summary`) without creating chunks.
- **`ML.PROCESS_DOCUMENT`** requires creating a Document AI processor (`INVOICE_PROCESSOR`, `EXPENSE_PROCESSOR`, `FORM_PARSER_PROCESSOR`) and a `CREATE MODEL ... REMOTE_SERVICE_TYPE = 'CLOUD_AI_DOCUMENT_V1'` handle, returning domain-specific normalized fields and confidence scores (`ml_process_document_result` JSON).

```python
invoice_uri = f'gs://{BUCKET}/{GCS_PREFIX}/docs/invoice_001.pdf'
conn_arg = f'{PROJECT_ID}.{LOCATION}.{CONNECTION_ID}'

# 1. AI.CHUNK_DOCUMENT: deterministic layout-preserving Markdown chunk(s)
df_chunked_inv = client.query(f"""
SELECT
  chunk_id,
  start_page,
  end_page,
  content
FROM AI.CHUNK_DOCUMENT(
  '{invoice_uri}',
  connection_id => '{conn_arg}',
  chunk_size => 500
)
WHERE status = ''
ORDER BY chunk_id
""").to_dataframe()

# 2. Multimodal AI.GENERATE: single-pass structured extraction + summary on the same PDF
df_gemini_inv = client.query(f"""
SELECT
  extracted.vendor,
  extracted.invoice_number,
  extracted.total_due,
  extracted.summary
FROM (
  SELECT
    AI.GENERATE(
      (
        'Extract the supplier name, invoice number, total amount due, and a one-sentence summary from this invoice: ',
        OBJ.MAKE_REF('{invoice_uri}', '{conn_arg}')
      ),
      connection_id => '{conn_arg}',
      endpoint => 'gemini-2.5-flash',
      output_schema => 'vendor STRING, invoice_number STRING, total_due FLOAT64, summary STRING'
    ) AS extracted
)
""").to_dataframe()

print('--- AI.CHUNK_DOCUMENT output (Markdown layout chunk) ---')
display(df_chunked_inv)
print('--- AI.GENERATE output (single-pass structured extraction) ---')
display(df_gemini_inv)
```

### Which one should you reach for?

| Dimension | `AI.CHUNK_DOCUMENT` | `AI.GENERATE` / `AI.GENERATE_TABLE` | `ML.PROCESS_DOCUMENT` |
|---|---|---|---|
| **Setup required** | Zero DDL (auto-creates `bq-created-layout-parser`) | Zero DDL (pass `ObjectRef` directly) | Manual Document AI processor + `CREATE MODEL ... REMOTE` |
| **Output shape** | Typed rows: `chunk_id`, `start_page`, `end_page`, `content`, `status` | Custom `STRING` or `STRUCT` (`output_schema`) | Processor-specific columns + `ml_process_document_result` `JSON` |
| **Determinism** | Deterministic across runs | Generative (LLM variability) | Deterministic per processor version |
| **Supported formats** | PDF, HTML, DOCX, PPTX, XLSX, XLSM | PDF, images, audio, video, text | Processor-dependent (PDF, TIFF, GIF, JPEG, PNG, etc.) |
| **Pricing model** | Document AI Layout Parser (`$10` / `1,000` pages; `$0` idle) | Vertex AI Gemini input + output tokens | Document AI per-page processor rate (`$0` idle) |
| **Best fit** | **Document RAG & hybrid search** (`AI.EMBED` + `VECTOR_SEARCH` / `AI.SEARCH`) | **Whole-document Q&A, summarization, or custom schema extraction** | **Standardized financial/form pipelines** (Invoices, Receipts, W-2s, IDs) |

---
## Examples — `%%bigquery` Magics

The same SQL patterns work directly in `%%bigquery` cells without Python string wrapping. Remember that IPython expands `{PROJECT_ID}` on the `%%bigquery` header line (setting the query's default project), so table names inside the SQL body reference `bq_ai_functions.<table_name>` directly.

### Chunk an Object Table inline, and chunk a public PDF into a DataFrame

Below we query our `bq_ai_functions.ai_chunk_document_docs` Object Table inline, then capture chunks from Google's public multi-page *CritterCuisine 5000* manual PDF into a pandas DataFrame (`df_public_manual`) using end-user credentials.

```sql
%%bigquery --project {PROJECT_ID}

SELECT
  REGEXP_EXTRACT(uri, r'[^/]+$') AS file_name,
  chunk_id,
  start_page,
  end_page,
  CHAR_LENGTH(content) AS char_len
FROM AI.CHUNK_DOCUMENT(
  TABLE `bq_ai_functions.ai_chunk_document_docs`,
  chunk_size => 250
)
WHERE status = ''
ORDER BY file_name, chunk_id
```

```sql
%%bigquery df_public_manual --project {PROJECT_ID}

SELECT
  chunk_id,
  start_page,
  end_page,
  CHAR_LENGTH(content) AS char_len,
  SUBSTR(REPLACE(content, '\n', ' ⏎ '), 1, 100) AS preview
FROM AI.CHUNK_DOCUMENT(
  'gs://cloud-samples-data/bigquery/tutorials/cymbal-pets/documents/crittercuisine_5000_user_manual.pdf',
  chunk_size => 500
)
WHERE status = ''
ORDER BY chunk_id
```

```python
print(f'Public manual produced {len(df_public_manual)} chunks:')
df_public_manual.head()
```

---
## Examples — BigFrames

Here we inspect `bigframes.bigquery.ai` directly to check whether a native `chunk_document` wrapper exists yet, then execute `AI.CHUNK_DOCUMENT` from BigFrames via `session.read_gbq_query()` so downstream operations stay lazy in BigQuery.

```python
import bigframes
import bigframes.bigquery as bbq
import bigframes.pandas as bpd

bpd.close_session()
bpd.options.bigquery.project = PROJECT_ID
bpd.options.bigquery.location = LOCATION

ai_methods = sorted(name for name in dir(bbq.ai) if not name.startswith('_'))
print(f'bigframes {bigframes.__version__} bbq.ai methods: {ai_methods}')
print(f"Native bbq.ai.chunk_document available: {hasattr(bbq.ai, 'chunk_document')}")

session = bpd.get_global_session()
bf_chunks = session.read_gbq_query(f"""
SELECT
  REGEXP_EXTRACT(uri, r'[^/]+$') AS file_name,
  chunk_id,
  start_page,
  end_page,
  CHAR_LENGTH(content) AS char_len
FROM AI.CHUNK_DOCUMENT(
  TABLE `{PROJECT_ID}.{DATASET_ID}.ai_chunk_document_docs`,
  chunk_size => 300
)
WHERE status = ''
ORDER BY file_name, chunk_id
""")
bf_chunks.to_pandas()
```
