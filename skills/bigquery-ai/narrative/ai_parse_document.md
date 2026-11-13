> **Source (`statmike/bigquery-data-science`):** **Notebook:** [`bigquery-ai/functions/ai_parse_document/ai_parse_document.ipynb`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ai/functions/ai_parse_document/ai_parse_document.ipynb) · **SQL:** [`bigquery-ai/functions/ai_parse_document/ai_parse_document.sql`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ai/functions/ai_parse_document/ai_parse_document.sql)

# AI.PARSE_DOCUMENT — BigQuery AI Functions

`AI.PARSE_DOCUMENT` is a scalar function (GA) that parses unstructured documents in Cloud Storage (or Google Drive via `ObjectRef`) — PDF, HTML, DOCX, PPTX, XLSX, and XLSM — into structured `JSON` directly in BigQuery SQL, with zero `CREATE MODEL` DDL and zero manual Document AI processor setup. On the first call in a project, BigQuery automatically provisions and reuses a shared Document AI Layout Parser processor (`bq-created-layout-parser`, `$0` idle holding fee, up to 130 pages per document) that extracts reading-order layout blocks, HTML tables, page numbers, and normalized bounding boxes:

```sql
AI.PARSE_DOCUMENT(
  [document => ] DOCUMENT
  [, connection_id => 'CONNECTION_ID']
  [, options => JSON '{"schema": "layout-v1" | "raw-docai"}']
) -> JSON
```

**When to use it:**
- You want element-level layout blocks (`title`, `heading`, `text`, `table`, `list_item`, `image`, `page_header`, `page_footer`) with 1-based page numbers, normalized `[min_y, min_x, max_y, max_x]` bounding boxes, and HTML `<table>...</table>` strings (`layout-v1`, default)
- You want to **parse once and chunk many times** by saving `options => JSON '{"schema": "raw-docai"}'` output in a `parsed_document` column and passing it into `functions/ai_chunk_document` (`AI.CHUNK_DOCUMENT`) at different `chunk_size` settings
- You want scalar per-row `JSON` output in a `SELECT` list without `CREATE MODEL` or manual processor lifecycle management

**Alternatives:**
- `functions/ai_chunk_document` (`AI.CHUNK_DOCUMENT`) — Table-valued function (TVF) that uses the same auto-provisioned `bq-created-layout-parser` processor (or accepts `raw-docai` JSON from `AI.PARSE_DOCUMENT`) to emit RAG-ready `chunk_id`, `start_page`, `end_page`, `content`, and `status` rows with ancestor section headings prepended
- `functions/ml_process_document` (`ML.PROCESS_DOCUMENT`) — Pre-trained specialized Document AI processors (Invoice Parser, Expense Parser, Form Parser, OCR on standalone images) via `CREATE MODEL ... REMOTE WITH CONNECTION ... OPTIONS(REMOTE_SERVICE_TYPE = 'CLOUD_AI_DOCUMENT_V1')`
- `functions/ai_generate` (`AI.GENERATE`) / `functions/ai_generate_table` (`AI.GENERATE_TABLE`) — Pass `ObjectRef` documents directly to Gemini when you want a single-pass summary, Q&A answer, or custom `output_schema` extraction over a whole document

### Choosing & Co-Using `AI.PARSE_DOCUMENT` and `AI.CHUNK_DOCUMENT`

Both functions share BigQuery's auto-provisioned `bq-created-layout-parser` processor (`$0` idle fee; PDF, HTML, DOCX, PPTX, XLSX, XLSM up to 130 pages), so you can use either one standalone or chain them together:

| Dimension | `AI.PARSE_DOCUMENT` Alone (Scalar `-> JSON`) | `functions/ai_chunk_document` (`AI.CHUNK_DOCUMENT`) Alone (TVF) | Both Together (`AI.PARSE_DOCUMENT` → `AI.CHUNK_DOCUMENT`) |
|---|---|---|---|
| **SQL Call & Schema** | `SELECT AI.PARSE_DOCUMENT(doc)` (`"layout-v1"`, default) | `FROM AI.CHUNK_DOCUMENT(source, chunk_size => N)` | Stage 1: `AI.PARSE_DOCUMENT(doc, options => JSON '{"schema": "raw-docai"}') AS parsed_document`<br>Stage 2: `FROM AI.CHUNK_DOCUMENT(TABLE parsed, chunk_size => N)` |
| **Row Cardinality** | **1 document in → 1 `JSON` value out** (`{metadata, blocks, errors}`) | **1 document in → $N$ chunk rows out** (`chunk_id`, `start_page`, `end_page`, `content`, `status`) | Stage 1 stores 1 `JSON` row per document; Stage 2 expands into $N$ chunk rows per `chunk_size` |
| **Structural Detail** | Element-level blocks (`title`, `heading`, `text`, `table`, `list_item`, `image`), HTML `<table>` strings, and normalized `[min_y, min_x, max_y, max_x]` `bbox` | Token-bounded text sections (`1..2000` tokens, default `1000`) with ancestor headings prepended | Full Document AI layout tree cached in BigQuery so `AI.CHUNK_DOCUMENT` can re-slice without calling Document AI again |
| **Success Filter** | `JSON_QUERY(doc, '$.errors') IS NULL AND doc IS NOT NULL` | `WHERE status = ''` | Stage 1: `JSON_QUERY(parsed_document, '$.errors') IS NULL`; Stage 2: `WHERE status = ''` |
| **Best For** | Extracting HTML tables, filtering specific block types (`WHERE type = 'table'`), or inspecting page coordinates | One-step RAG chunking when a single `chunk_size` is already chosen | **"Parse Once, Chunk Many Times"** — tuning `chunk_size` (e.g. `150` vs `250` vs `500`) or feeding multiple RAG pipelines while paying for Document AI parsing only once |

**Featured in:** `workflows/document_rag` (Document RAG)

**References:** `reference/document-processing.md#aiparse_document` (Document Processing reference) | `RESOURCES.md` (Full syntax reference) | [Official documentation](https://docs.cloud.google.com/bigquery/docs/reference/standard-sql/bigqueryml-syntax-ai-parse-document) | `setup` (Setup guide)

---
## Setup

Set your project and location, enable the Document AI API, configure the shared Cloud resource connection, and stage a compact multi-format document set in Cloud Storage.

> **How authentication and processor provisioning work:**
> - **Auto-provisioned Layout Parser:** `AI.PARSE_DOCUMENT` requires `documentai.googleapis.com`. The first call in a project automatically creates a single Document AI Layout Parser processor named `bq-created-layout-parser` (`LAYOUT_PARSER_PROCESSOR`) and reuses it on every subsequent call at zero idle cost (`$10` per `1,000` processed pages; up to **130 pages** per document).
> - **End-user credentials (EUC) vs Cloud resource connection:** Direct `'gs://...'` URI strings and 1-argument `OBJ.MAKE_REF(uri)` run under the caller's own IAM roles by default; Object Tables, `OBJ.LIST(...)`, 2-argument `OBJ.MAKE_REF(uri, connection_id)`, and explicit `connection_id => ...` calls delegate Storage and Document AI access to the connection's service account. Google Drive files are also supported when passed as an `ObjectRef` value (passing a Drive URI directly as a `STRING` is not supported).
> - **Regional availability:** Supported in `US` and `EU` multi-regions and in US/EU single regions **except `europe-west2` (London) and `europe-west6` (Zürich)**.
> - **VPC Service Controls:** Delegated `ObjectRef` inputs (`connection_id`, Object Tables, `OBJ.LIST`, and 2-argument `OBJ.MAKE_REF(uri, connection_id)`) mint signed HTTPS URLs and fail inside VPC-SC perimeters (`HTTP links are not supported for requests restricted by VPCSC`). Inside VPC-SC, authenticate with EUC (`'gs://...'` literal or 1-argument `OBJ.MAKE_REF(uri)`).

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
GCS_PREFIX = 'bq_ai_functions/ai_parse_document'
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

`AI.PARSE_DOCUMENT` checks Document AI permissions differently depending on whether the project's `bq-created-layout-parser` processor has already been auto-created:

| Principal | Role | Why it is needed |
|---|---|---|
| Query caller (EUC or connection path) | `roles/bigquery.jobUser` | Run BigQuery queries in the project |
| Query caller (connection path) | `roles/bigquery.connectionUser` | Use the Cloud resource connection |
| EUC caller *or* Connection SA | `roles/storage.objectViewer` | Read source documents in Cloud Storage |
| EUC caller *or* Connection SA | `roles/documentai.editor` *(first call)* / `roles/documentai.viewer` *(thereafter)* | Auto-create `bq-created-layout-parser` on the very first call in the project; invoke it on subsequent calls |
| Connection SA | `roles/serviceusage.serviceUsageConsumer` | Consume Cloud AI APIs through the connection |
| Connection SA *(Example 7 only)* | `roles/aiplatform.user` | Call Gemini via `AI.GENERATE` in the side-by-side comparison |

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
    'roles/aiplatform.user',     # used only for the AI.GENERATE comparison in Example 7
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

To test multi-page layout extraction, HTML table blocks, `layout-v1` vs `raw-docai` output schemas, `AI.CHUNK_DOCUMENT` chaining, and per-row error reporting without external dependencies, we stage six small files under `gs://{BUCKET}/bq_ai_functions/ai_parse_document/` (and delete all six at the end of the notebook):

1. `docs/handbook_multipage.pdf` — 4-page *Cloud Operations Runbook* rendered in memory with `weasyprint` (headings, an SLO table, a triage checklist, and explicit page breaks)
2. `docs/invoice_001.pdf` — Synthetic 1-page service invoice from `data/documents` (`data/documents/invoices/`) (with an in-memory fallback when running standalone in Colab), used in Example 7 to compare `AI.PARSE_DOCUMENT`, `AI.CHUNK_DOCUMENT`, `AI.GENERATE`, and `ML.PROCESS_DOCUMENT`
3. `formats/release_notes.html` — Structured HTML release notes (`text/html`)
4. `formats/vendor_policy.docx` — Word document (`application/vnd.openxmlformats-officedocument.wordprocessingml.document`)
5. `formats/slo_matrix.xlsx` — Excel spreadsheet (`application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`)
6. `unsupported/plain_note.txt` — Plain-text file (`text/plain`) intentionally staged to trigger a structured per-row `errors` entry without aborting the query

We also create an Object Table (`bq_ai_functions.ai_parse_document_docs`) over `docs/*.pdf` so Example 3 can compare all four input shapes side by side.

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
    '<p>Introduced scalar layout-aware document parsing and raw-docai chunk chaining.</p>'
    '<h2>Upgrade Notes</h2>'
    '<ul><li>Inspect blocks in reading order with layout-v1 or chain raw-docai into AI.CHUNK_DOCUMENT.</li>'
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
txt_bytes = b'Plain text note: text/plain is intentionally unsupported by AI.PARSE_DOCUMENT.'

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
CREATE OR REPLACE EXTERNAL TABLE `{PROJECT_ID}.{DATASET_ID}.ai_parse_document_docs`
WITH CONNECTION `{PROJECT_ID}.{LOCATION}.{CONNECTION_ID}`
OPTIONS (
  object_metadata = 'SIMPLE',
  uris = ['gs://{BUCKET}/{GCS_PREFIX}/docs/*.pdf']
)
""").result()

print(f'Staged {len(staged_payloads)} files under gs://{BUCKET}/{GCS_PREFIX}/')
print(f'Object table {DATASET_ID}.ai_parse_document_docs ready')
```

---
## Examples — Python Client

`AI.PARSE_DOCUMENT` is a **scalar function** that takes a document (`'gs://...'` URI string or `ObjectRef` struct) and returns a `JSON` object:

```sql
AI.PARSE_DOCUMENT(
  [document => ] DOCUMENT
  [, connection_id => 'CONNECTION_ID']
  [, options => JSON '{"schema": "layout-v1" | "raw-docai"}']
) -> JSON
```

| Argument | Type | Default | Notes |
|---|---|---|---|
| `document` | `STRING` or `STRUCT` (`ObjectRef`) | *(required)* | Positional or named (`document => ...`). Accepts `'gs://bucket/path/file.pdf'` or an `ObjectRef` from `OBJ.MAKE_REF`, `OBJ.LIST`, or an Object Table `ref` column |
| `connection_id` | `STRING` | Caller EUC (or `ObjectRef` authorizer) | Format `'LOCATION.CONNECTION_ID'` or `'PROJECT_ID.LOCATION.CONNECTION_ID'` |
| `options` | `JSON` | `JSON '{"schema": "layout-v1"}'` | `{"schema": "layout-v1"}` returns flat reading-order blocks (`id`, `type`, `content`, `page_number`, `bbox`); `{"schema": "raw-docai"}` returns the full Document AI `DocumentLayout` tree (used for chaining into `AI.CHUNK_DOCUMENT`) |

### Example 1: Simplest starter call — single `'gs://...'` URI with End-User Credentials & `layout-v1` (default)

Pass a `'gs://...'` URI directly to `AI.PARSE_DOCUMENT`. With no `connection_id` and no `options`, BigQuery authenticates with your end-user credentials (EUC), uses the default `layout-v1` schema, and returns a `JSON` object with:

- `metadata.schema`: `"layout-v1"`
- `blocks`: reading-order array of layout blocks, where each block contains:
  - `id` (`INT64`, 0-based block index)
  - `type` (`STRING`: `title`, `heading`, `text`, `table`, `list_item`, `image`, `page_header`, or `page_footer`)
  - `page_number` (`INT64`, 1-based page number)
  - `bbox` (`ARRAY<FLOAT64>`: normalized `[min_y, min_x, max_y, max_x]` coordinates in `[0, 1]`)
  - `content` (`STRING`: extracted text, or an HTML `<table>...</table>` string when `type = "table"`)
- `errors`: omitted (`NULL`) when parsing succeeds; populated as an array of `{"code": "...", "message": "..."}` objects if parsing fails

```python
import json

query = f"""
WITH Parsed AS (
  SELECT
    AI.PARSE_DOCUMENT(
      'gs://{BUCKET}/{GCS_PREFIX}/docs/handbook_multipage.pdf'
    ) AS parsed_doc
)
SELECT
  JSON_VALUE(parsed_doc.metadata.schema) AS schema_version,
  ARRAY_LENGTH(JSON_QUERY_ARRAY(parsed_doc.blocks)) AS block_count,
  JSON_QUERY(parsed_doc, '$.errors') AS errors_field,
  TO_JSON_STRING(parsed_doc) AS parsed_json
FROM Parsed
"""
df_ex1 = client.query(query).to_dataframe()
row = df_ex1.iloc[0]
print(f"Schema: {row['schema_version']} | Total blocks: {row['block_count']} | errors field: {row['errors_field']}")

parsed_obj = json.loads(row['parsed_json'])
df_first_blocks = pd.DataFrame(parsed_obj['blocks'][:6])[['id', 'type', 'page_number', 'bbox', 'content']]
df_first_blocks
```

### Example 2: Flattening `blocks` into relational SQL rows with `UNNEST(JSON_QUERY_ARRAY(parsed_doc.blocks))`

Because `AI.PARSE_DOCUMENT` returns a `JSON` value, you can unpack `parsed_doc.blocks` into typed relational rows in SQL using `UNNEST(JSON_QUERY_ARRAY(parsed_doc.blocks)) AS block`:

- `INT64(block.id) AS block_id`
- `JSON_VALUE(block.type) AS block_type`
- `INT64(block.page_number) AS page_number`
- `TO_JSON_STRING(block.bbox) AS bbox`
- `JSON_VALUE(block.content) AS content`

Notice how the Service Level Objectives table on page 2 is extracted with `block_type = 'table'` and serialized as a complete HTML `<table><thead>...</thead><tbody>...</tbody></table>` string!

```python
flatten_query = f"""
WITH Parsed AS (
  SELECT
    AI.PARSE_DOCUMENT(
      'gs://{BUCKET}/{GCS_PREFIX}/docs/handbook_multipage.pdf'
    ) AS parsed_doc
)
SELECT
  INT64(block.id) AS block_id,
  JSON_VALUE(block.type) AS block_type,
  INT64(block.page_number) AS page_number,
  TO_JSON_STRING(block.bbox) AS bbox,
  JSON_VALUE(block.content) AS content
FROM Parsed,
UNNEST(JSON_QUERY_ARRAY(parsed_doc.blocks)) AS block
ORDER BY block_id
"""
df_blocks = client.query(flatten_query).to_dataframe()

summary_by_type = (
    df_blocks.groupby(['page_number', 'block_type'], as_index=False)
    .agg(block_count=('block_id', 'count'))
    .sort_values(['page_number', 'block_type'])
)
print('--- Block counts by page_number and block_type ---')
display(summary_by_type)

print('--- Flattened layout-v1 blocks (including HTML <table> on page 2) ---')
df_blocks
```

### Example 3: All input & authentication shapes

Because `AI.PARSE_DOCUMENT` is a standard scalar function, you can invoke it on any `STRING` URI or `ObjectRef` expression in a `SELECT` list:

1. **Shape A — `'gs://...'` URI string with `connection_id`:** Pass a URI string (positional or `document => ...`) and delegate authentication to a Cloud resource connection via `connection_id => '{PROJECT_ID}.{LOCATION}.{CONNECTION_ID}'`.
2. **Shape B — Inline `OBJ.MAKE_REF(uri, connection_id)`:** Construct an `ObjectRef` inline without creating an Object Table (or use 1-argument `OBJ.MAKE_REF(uri)` for EUC).
3. **Shape C — Multi-document folder parsing via `FROM OBJ.LIST('gs://.../docs/*.pdf', connection_id)`:** Parse an entire Cloud Storage prefix or wildcard pattern on the fly without DDL.
4. **Shape D — Querying an Object Table (`FROM \`{PROJECT_ID}.{DATASET_ID}.ai_parse_document_docs\``):** Pass the table's `ref` column (alongside `uri`, `content_type`, `size`, and other object metadata columns).

> **Google Drive & VPC Service Controls notes:**
> - **Google Drive files** are supported when passed as an `ObjectRef` value (passing a Google Drive URI directly as a `STRING` is not supported).
> - **VPC Service Controls:** Inside a VPC-SC perimeter, delegated `ObjectRef` inputs (`connection_id`, Object Tables, `OBJ.LIST`, and 2-argument `OBJ.MAKE_REF(uri, connection_id)`) fail because they mint signed HTTPS URLs (`HTTP links are not supported for requests restricted by VPCSC`). Inside VPC-SC, use EUC (`'gs://...'` literal or 1-argument `OBJ.MAKE_REF(uri)`).

```python
conn_arg = f'{PROJECT_ID}.{LOCATION}.{CONNECTION_ID}'
invoice_uri = f'gs://{BUCKET}/{GCS_PREFIX}/docs/invoice_001.pdf'

shapes_query = f"""
-- Shape A: 'gs://...' URI string with explicit connection_id (and named document => argument)
SELECT
  'Shape A: URI string + connection_id' AS input_shape,
  REGEXP_EXTRACT('{invoice_uri}', r'[^/]+$') AS file_name,
  JSON_VALUE(parsed_doc.metadata.schema) AS schema_version,
  ARRAY_LENGTH(JSON_QUERY_ARRAY(parsed_doc.blocks)) AS block_count
FROM (
  SELECT AI.PARSE_DOCUMENT(
    document => '{invoice_uri}',
    connection_id => '{conn_arg}'
  ) AS parsed_doc
)

UNION ALL

-- Shape B: Inline OBJ.MAKE_REF(uri, connection_id)
SELECT
  'Shape B: Inline OBJ.MAKE_REF(uri, conn)' AS input_shape,
  REGEXP_EXTRACT('{invoice_uri}', r'[^/]+$') AS file_name,
  JSON_VALUE(parsed_doc.metadata.schema) AS schema_version,
  ARRAY_LENGTH(JSON_QUERY_ARRAY(parsed_doc.blocks)) AS block_count
FROM (
  SELECT AI.PARSE_DOCUMENT(
    OBJ.MAKE_REF('{invoice_uri}', '{conn_arg}')
  ) AS parsed_doc
)

UNION ALL

-- Shape C: Multi-document folder parsing via FROM OBJ.LIST('gs://.../docs/*.pdf', connection_id)
SELECT
  'Shape C: FROM OBJ.LIST(wildcard, conn)' AS input_shape,
  REGEXP_EXTRACT(ref.uri, r'[^/]+$') AS file_name,
  JSON_VALUE(parsed_doc.metadata.schema) AS schema_version,
  ARRAY_LENGTH(JSON_QUERY_ARRAY(parsed_doc.blocks)) AS block_count
FROM (
  SELECT
    ref,
    AI.PARSE_DOCUMENT(ref) AS parsed_doc
  FROM OBJ.LIST('gs://{BUCKET}/{GCS_PREFIX}/docs/*.pdf', '{conn_arg}')
)

UNION ALL

-- Shape D: Querying an Object Table (FROM bq_ai_functions.ai_parse_document_docs)
SELECT
  'Shape D: Object Table (ref column)' AS input_shape,
  REGEXP_EXTRACT(uri, r'[^/]+$') AS file_name,
  JSON_VALUE(parsed_doc.metadata.schema) AS schema_version,
  ARRAY_LENGTH(JSON_QUERY_ARRAY(parsed_doc.blocks)) AS block_count
FROM (
  SELECT
    uri,
    AI.PARSE_DOCUMENT(ref) AS parsed_doc
  FROM `{PROJECT_ID}.{DATASET_ID}.ai_parse_document_docs`
)
ORDER BY input_shape, file_name
"""
client.query(shapes_query).to_dataframe()
```

### Example 4: Output schemas — `layout-v1` (default) vs `raw-docai` (`options => JSON '{"schema": "raw-docai"}'`)

`AI.PARSE_DOCUMENT` supports two output schemas via `options => JSON '{"schema": "..."}'`:

| Schema | `metadata.schema` | Block representation | Best for |
|---|---|---|---|
| **`layout-v1` *(default)*** | `"layout-v1"` | Flat reading-order array (`id`, `type`, `page_number`, `bbox`, `content` with HTML `<table>` strings) | Direct SQL analytics, bounding-box inspection, and element-level filtering (`UNNEST(JSON_QUERY_ARRAY(parsed_doc.blocks))`) |
| **`raw-docai`** | `"raw-docai"` | Nested Document AI `DocumentLayoutBlock` tree in camelCase (`blockId`, `pageSpan.pageStart`/`pageEnd`, `textBlock.type`, `textBlock.text`, and recursive child `textBlock.blocks`, plus `tableBlock` / `listBlock`) | Chaining into `functions/ai_chunk_document` (`AI.CHUNK_DOCUMENT`) via a `parsed_document` column, or preserving the full hierarchical section tree |

Passing any schema name other than `"layout-v1"` or `"raw-docai"` fails fast at query analysis time (`400 Unsupported document parsing schema`).

```python
from google.api_core.exceptions import GoogleAPIError

schema_compare_query = f"""
WITH BothSchemas AS (
  SELECT
    AI.PARSE_DOCUMENT(
      'gs://{BUCKET}/{GCS_PREFIX}/docs/handbook_multipage.pdf',
      options => JSON '{{"schema": "layout-v1"}}'
    ) AS doc_layout_v1,
    AI.PARSE_DOCUMENT(
      'gs://{BUCKET}/{GCS_PREFIX}/docs/handbook_multipage.pdf',
      options => JSON '{{"schema": "raw-docai"}}'
    ) AS doc_raw_docai
)
SELECT
  JSON_VALUE(doc_layout_v1.metadata.schema) AS layout_v1_schema,
  ARRAY_LENGTH(JSON_QUERY_ARRAY(doc_layout_v1.blocks)) AS layout_v1_flat_blocks,
  TO_JSON_STRING(JSON_QUERY_ARRAY(doc_layout_v1.blocks)[OFFSET(0)]) AS layout_v1_first_block,
  JSON_VALUE(doc_raw_docai.metadata.schema) AS raw_docai_schema,
  ARRAY_LENGTH(JSON_QUERY_ARRAY(doc_raw_docai.blocks)) AS raw_docai_root_blocks,
  ARRAY_LENGTH(JSON_QUERY_ARRAY(doc_raw_docai.blocks[0].textBlock.blocks)) AS raw_docai_root0_children,
  JSON_VALUE(doc_raw_docai.blocks[0].blockId) AS raw_docai_first_block_id,
  JSON_VALUE(doc_raw_docai.blocks[0].textBlock.type) AS raw_docai_first_block_type,
  JSON_VALUE(doc_raw_docai.blocks[0].textBlock.text) AS raw_docai_first_block_text
FROM BothSchemas
"""
df_schemas = client.query(schema_compare_query).to_dataframe()
display(df_schemas[[
    'layout_v1_schema', 'layout_v1_flat_blocks',
    'raw_docai_schema', 'raw_docai_root_blocks', 'raw_docai_root0_children',
    'raw_docai_first_block_type', 'raw_docai_first_block_text',
]])
print('layout-v1 first block JSON:', df_schemas['layout_v1_first_block'].iloc[0])

# Boundary probe: unknown schema in options raises an analysis-time 400 error
try:
    client.query(f"""
    SELECT AI.PARSE_DOCUMENT(
      'gs://{BUCKET}/{GCS_PREFIX}/docs/invoice_001.pdf',
      options => JSON '{{"schema": "unknown"}}'
    )
    """).result()
except GoogleAPIError as exc:
    msg = exc.message.splitlines()[0].replace(PROJECT_ID, 'your-gcp-project-id')
    print(f'\n[options => JSON \'{{"schema": "unknown"}}\']\n  -> {msg}')
```

### Example 5: Chaining `AI.PARSE_DOCUMENT` (`raw-docai`) into `AI.CHUNK_DOCUMENT` ("Parse Once, Chunk Many Times")

`functions/ai_chunk_document` (`AI.CHUNK_DOCUMENT`) accepts a `TABLE` or `(SELECT ...)` subquery containing a `JSON` column named **`parsed_document`**. This unlocks a powerful two-stage pattern:

1. **Parse once:** Call `AI.PARSE_DOCUMENT(..., options => JSON '{"schema": "raw-docai"}') AS parsed_document` (and optionally materialize it to a BigQuery table).
2. **Chunk many times:** Run `AI.CHUNK_DOCUMENT` over `parsed_document` with different `chunk_size` settings (`150` vs `800` tokens) in pure BigQuery SQL without re-invoking Document AI or paying per-page Layout Parser fees again!

> **Critical schema requirement (`raw-docai` only):**
> `AI.CHUNK_DOCUMENT` requires the hierarchical `raw-docai` layout tree so it can prepend ancestor headings and compute token boundaries. If you pass the default `layout-v1` output into `AI.CHUNK_DOCUMENT`, it returns a per-row failure:
> `status = 'INVALID_ARGUMENT: Unsupported document schema: layout-v1'` (`content = NULL`).

```python
conn_arg = f'{PROJECT_ID}.{LOCATION}.{CONNECTION_ID}'
handbook_uri = f'gs://{BUCKET}/{GCS_PREFIX}/docs/handbook_multipage.pdf'

# 1. Parse once with raw-docai, then chunk at two different granularities (150 vs 800 tokens)
chain_query = f"""
WITH ParsedOnce AS (
  SELECT
    'DOC-RUNBOOK' AS doc_id,
    AI.PARSE_DOCUMENT(
      '{handbook_uri}',
      connection_id => '{conn_arg}',
      options => JSON '{{"schema": "raw-docai"}}'
    ) AS parsed_document
),
FineChunks AS (
  SELECT 150 AS target_tokens, doc_id, chunk_id, start_page, end_page, content
  FROM AI.CHUNK_DOCUMENT((SELECT * FROM ParsedOnce), chunk_size => 150)
  WHERE status = ''
),
CoarseChunks AS (
  SELECT 800 AS target_tokens, doc_id, chunk_id, start_page, end_page, content
  FROM AI.CHUNK_DOCUMENT((SELECT * FROM ParsedOnce), chunk_size => 800)
  WHERE status = ''
),
Combined AS (
  SELECT * FROM FineChunks
  UNION ALL
  SELECT * FROM CoarseChunks
)
SELECT
  doc_id,
  target_tokens,
  COUNT(*) AS chunk_count,
  MIN(CHAR_LENGTH(content)) AS min_chars,
  CAST(ROUND(AVG(CHAR_LENGTH(content))) AS INT64) AS avg_chars,
  MAX(CHAR_LENGTH(content)) AS max_chars
FROM Combined
GROUP BY doc_id, target_tokens
ORDER BY target_tokens
"""
print('--- Parse Once (raw-docai), Chunk Many Times (chunk_size 150 vs 800) ---')
display(client.query(chain_query).to_dataframe())

# 2. Empirical gotcha probe: passing default layout-v1 into AI.CHUNK_DOCUMENT
gotcha_query = f"""
SELECT
  doc_id,
  chunk_id,
  content,
  status
FROM AI.CHUNK_DOCUMENT(
  (
    SELECT
      'DOC-INV-001' AS doc_id,
      AI.PARSE_DOCUMENT(
        'gs://{BUCKET}/{GCS_PREFIX}/docs/invoice_001.pdf',
        connection_id => '{conn_arg}'
        -- default options => JSON '{{"schema": "layout-v1"}}'
      ) AS parsed_document
  ),
  chunk_size => 300
)
"""
print('--- Gotcha check: passing default layout-v1 into AI.CHUNK_DOCUMENT ---')
display(client.query(gotcha_query).to_dataframe())
```

### Example 6: Multi-format inputs (`.html`, `.docx`, `.xlsx`) & the 3-way error contract

At GA, `AI.PARSE_DOCUMENT` supports **PDF** (`.pdf`), **HTML** (`.html`), **Word** (`.docx`), **PowerPoint** (`.pptx`), and **Excel** (`.xlsx`, `.xlsm`). Per-document errors do **not** abort a multi-row query — instead, `AI.PARSE_DOCUMENT` follows a clean **3-way outcome contract**:

| Input outcome | Returned `JSON` | `blocks` | `errors` |
|---|---|---|---|
| `NULL` input (`CAST(NULL AS STRING)`) | SQL `NULL` | `NULL` | `NULL` |
| Valid supported document (`.pdf`, `.html`, `.docx`, `.pptx`, `.xlsx`, `.xlsm`) | Populated `JSON` object | Non-empty array of blocks | Omitted (`JSON_QUERY(parsed_doc, '$.errors') IS NULL`) |
| Unsupported MIME type (`.txt` `text/plain`), >130-page PDF, or missing GCS object (`404`) | Populated `JSON` object | Empty array `[]` | Array of error objects: `[{"code": "INVALID_ARGUMENT" \| "NOT_FOUND", "message": "..."}]` |

> **Production filtering rule:** Always filter valid parsed documents with:
> `WHERE parsed_doc IS NOT NULL AND JSON_QUERY(parsed_doc, '$.errors') IS NULL`

```python
conn_arg = f'{PROJECT_ID}.{LOCATION}.{CONNECTION_ID}'

error_contract_query = f"""
WITH MixedInputs AS (
  SELECT '0_null_input'       AS input_label, CAST(NULL AS STRING) AS uri
  UNION ALL
  SELECT '1_html_valid'       AS input_label, 'gs://{BUCKET}/{GCS_PREFIX}/formats/release_notes.html'    AS uri
  UNION ALL
  SELECT '2_docx_valid'       AS input_label, 'gs://{BUCKET}/{GCS_PREFIX}/formats/vendor_policy.docx'    AS uri
  UNION ALL
  SELECT '3_xlsx_valid'       AS input_label, 'gs://{BUCKET}/{GCS_PREFIX}/formats/slo_matrix.xlsx'       AS uri
  UNION ALL
  SELECT '4_txt_unsupported'  AS input_label, 'gs://{BUCKET}/{GCS_PREFIX}/unsupported/plain_note.txt'    AS uri
  UNION ALL
  SELECT '5_pdf_missing_blob' AS input_label, 'gs://{BUCKET}/{GCS_PREFIX}/docs/missing_document_404.pdf' AS uri
),
Parsed AS (
  SELECT
    input_label,
    AI.PARSE_DOCUMENT(uri, connection_id => '{conn_arg}') AS parsed_doc
  FROM MixedInputs
)
SELECT
  input_label,
  CASE
    WHEN parsed_doc IS NULL THEN 'sql_null'
    WHEN JSON_QUERY(parsed_doc, '$.errors') IS NULL THEN 'valid_document'
    ELSE 'document_error'
  END AS row_outcome,
  ARRAY_LENGTH(JSON_QUERY_ARRAY(parsed_doc.blocks)) AS block_count,
  JSON_VALUE(parsed_doc.errors[0].code) AS error_code,
  REGEXP_REPLACE(
    IFNULL(JSON_VALUE(parsed_doc.errors[0].message), ''),
    r'{PROJECT_ID}',
    'your-gcp-project-id'
  ) AS error_message,
  SUBSTR(REPLACE(JSON_VALUE(parsed_doc.blocks[0].content), '\\n', ' ⏎ '), 1, 90) AS first_block_preview
FROM Parsed
ORDER BY input_label
"""
df_contract = client.query(error_contract_query).to_dataframe()
df_contract
```

### Example 7: Side-by-side comparison — `AI.PARSE_DOCUMENT` vs `AI.CHUNK_DOCUMENT` vs `ML.PROCESS_DOCUMENT` vs `AI.GENERATE`

BigQuery provides four distinct tools for unstructured documents in Cloud Storage. Below we run `AI.PARSE_DOCUMENT`, `AI.CHUNK_DOCUMENT`, and multimodal `AI.GENERATE` (`endpoint => 'gemini-3.8-flash'`) on the exact same synthetic invoice (`invoice_001.pdf`), and compare all four alongside `functions/ml_process_document` (`ML.PROCESS_DOCUMENT`):

- **`AI.PARSE_DOCUMENT`** (scalar -> `JSON`) returns structured reading-order layout blocks (`title`, `heading`, `text`, HTML `<table>`, `bbox`, `page_number`) or the `raw-docai` layout tree.
- **`AI.CHUNK_DOCUMENT`** (TVF -> rows) packs those layout blocks into token-bounded Markdown chunks (`chunk_id`, `start_page`, `end_page`, `content`, `status`) with ancestor headings prepended for RAG.
- **`AI.GENERATE`** (scalar -> `STRUCT`) reads the `ObjectRef` directly with Gemini in a single pass to synthesize or extract custom typed fields (`vendor`, `invoice_number`, `total_due`, `summary`).
- **`ML.PROCESS_DOCUMENT`** (TVF -> rows) calls specialized Document AI processors (`INVOICE_PROCESSOR`, `EXPENSE_PROCESSOR`, `FORM_PARSER_PROCESSOR`, `OCR_PROCESSOR`) via a `CREATE MODEL ... REMOTE_SERVICE_TYPE = 'CLOUD_AI_DOCUMENT_V1'` handle.

```python
invoice_uri = f'gs://{BUCKET}/{GCS_PREFIX}/docs/invoice_001.pdf'
conn_arg = f'{PROJECT_ID}.{LOCATION}.{CONNECTION_ID}'

# 1. AI.PARSE_DOCUMENT: element-level layout blocks (including HTML <table> and bounding boxes)
df_parsed_inv = client.query(f"""
WITH Parsed AS (
  SELECT AI.PARSE_DOCUMENT('{invoice_uri}', connection_id => '{conn_arg}') AS parsed_doc
)
SELECT
  INT64(block.id) AS block_id,
  JSON_VALUE(block.type) AS block_type,
  INT64(block.page_number) AS page_number,
  TO_JSON_STRING(block.bbox) AS bbox,
  SUBSTR(REPLACE(JSON_VALUE(block.content), '\\n', ' '), 1, 110) AS content_preview
FROM Parsed,
UNNEST(JSON_QUERY_ARRAY(parsed_doc.blocks)) AS block
ORDER BY block_id
""").to_dataframe()

# 2. AI.CHUNK_DOCUMENT: token-bounded RAG chunk(s)
df_chunked_inv = client.query(f"""
SELECT
  chunk_id,
  start_page,
  end_page,
  CHAR_LENGTH(content) AS char_len,
  SUBSTR(REPLACE(content, '\\n', ' ⏎ '), 1, 120) AS chunk_preview
FROM AI.CHUNK_DOCUMENT(
  '{invoice_uri}',
  connection_id => '{conn_arg}',
  chunk_size => 500
)
WHERE status = ''
ORDER BY chunk_id
""").to_dataframe()

# 3. Multimodal AI.GENERATE: single-pass structured extraction + summary on the same PDF
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
      endpoint => 'gemini-3.8-flash',
      output_schema => 'vendor STRING, invoice_number STRING, total_due FLOAT64, summary STRING'
    ) AS extracted
)
""").to_dataframe()

print('--- 1. AI.PARSE_DOCUMENT output (element-level layout-v1 blocks) ---')
display(df_parsed_inv)
print('--- 2. AI.CHUNK_DOCUMENT output (RAG-ready Markdown chunk) ---')
display(df_chunked_inv)
print('--- 3. AI.GENERATE output (single-pass structured extraction) ---')
display(df_gemini_inv)
```

### Which one should you reach for?

| Dimension | `AI.PARSE_DOCUMENT` | `AI.CHUNK_DOCUMENT` | `AI.GENERATE` / `AI.GENERATE_TABLE` | `ML.PROCESS_DOCUMENT` |
|---|---|---|---|---|
| **Function type** | Scalar (`-> JSON`) | Table-valued function (`FROM AI.CHUNK_DOCUMENT(...)`) | Scalar (`-> STRUCT`) / TVF | Table-valued function (`FROM ML.PROCESS_DOCUMENT(...)`) |
| **Setup required** | Zero DDL (auto-creates `bq-created-layout-parser`) | Zero DDL (reuses `bq-created-layout-parser` or takes `parsed_document`) | Zero DDL (pass `ObjectRef` directly) | Manual Document AI processor + `CREATE MODEL ... REMOTE` |
| **Output shape** | `JSON` (`layout-v1` blocks with HTML `<table>` & `bbox`, or `raw-docai` tree) | Typed rows: `chunk_id`, `start_page`, `end_page`, `content`, `status` | Custom `STRING` or `STRUCT` (`output_schema`) | Processor-specific columns + `ml_process_document_result` `JSON` |
| **Determinism** | Deterministic across runs | Deterministic across runs | Generative (LLM variability) | Deterministic per processor version |
| **Supported formats** | PDF (<=130 pages), HTML, DOCX, PPTX, XLSX, XLSM | PDF (<=500 pages), HTML, DOCX, PPTX, XLSX, XLSM | PDF, images, audio, video, text | Processor-dependent (PDF, TIFF, GIF, JPEG, PNG, etc.) |
| **Pricing model** | Document AI Layout Parser (`$10` / `1,000` pages; `$0` idle) | Document AI Layout Parser (`$10` / `1,000` pages; `$0` for `parsed_document` input) | Vertex AI Gemini input + output tokens | Document AI per-page processor rate (`$0` idle) |
| **Best fit** | **Element-level layout & table extraction**, bounding boxes, or **parse-once / chunk-many** (`raw-docai`) | **Document RAG & hybrid search** (`AI.EMBED` + `VECTOR_SEARCH` / `AI.SEARCH`) | **Whole-document Q&A, summarization, or custom schema extraction** | **Standardized financial/form pipelines** (Invoices, Receipts, W-2s, IDs, standalone image OCR) |

---
## Examples — `%%bigquery` Magics

The same SQL patterns work directly in `%%bigquery` cells without Python string wrapping. Remember that IPython expands `{PROJECT_ID}` on the `%%bigquery` header line (setting the query's default project), so table names inside the SQL body reference `bq_ai_functions.<table_name>` directly.

### Flatten blocks from an Object Table inline, and parse a public PDF into a DataFrame

Below we flatten `layout-v1` blocks across our `bq_ai_functions.ai_parse_document_docs` Object Table inline, then capture block counts by type from Google's public multi-page *CritterCuisine 5000* manual PDF into a pandas DataFrame (`df_public_blocks`) using end-user credentials.

```sql
%%bigquery --project {PROJECT_ID}

WITH ParsedDocs AS (
  SELECT
    REGEXP_EXTRACT(uri, r'[^/]+$') AS file_name,
    AI.PARSE_DOCUMENT(ref) AS parsed_doc
  FROM `bq_ai_functions.ai_parse_document_docs`
)
SELECT
  file_name,
  JSON_VALUE(block.type) AS block_type,
  COUNT(*) AS block_count
FROM ParsedDocs,
UNNEST(JSON_QUERY_ARRAY(parsed_doc.blocks)) AS block
GROUP BY file_name, block_type
ORDER BY file_name, block_count DESC
```

```sql
%%bigquery df_public_blocks --project {PROJECT_ID}

WITH ParsedManual AS (
  SELECT
    AI.PARSE_DOCUMENT(
      'gs://cloud-samples-data/bigquery/tutorials/cymbal-pets/documents/crittercuisine_5000_user_manual.pdf'
    ) AS parsed_doc
)
SELECT
  INT64(block.id) AS block_id,
  JSON_VALUE(block.type) AS block_type,
  INT64(block.page_number) AS page_number,
  SUBSTR(REPLACE(JSON_VALUE(block.content), '\n', ' ⏎ '), 1, 100) AS preview
FROM ParsedManual,
UNNEST(JSON_QUERY_ARRAY(parsed_doc.blocks)) AS block
ORDER BY block_id
```

```python
print(f'Public manual produced {len(df_public_blocks)} layout-v1 blocks across {df_public_blocks["page_number"].nunique()} pages:')
df_public_blocks.head(8)
```

---
## Examples — BigFrames

Here we inspect `bigframes.bigquery.ai` directly to check whether a native `parse_document` wrapper exists yet, then execute `AI.PARSE_DOCUMENT` from BigFrames via `session.read_gbq_query()` so downstream operations stay lazy in BigQuery.

```python
import bigframes
import bigframes.bigquery as bbq
import bigframes.pandas as bpd

bpd.close_session()
bpd.options.bigquery.project = PROJECT_ID
bpd.options.bigquery.location = LOCATION

ai_methods = sorted(name for name in dir(bbq.ai) if not name.startswith('_'))
print(f'bigframes {bigframes.__version__} bbq.ai methods: {ai_methods}')
print(f"Native bbq.ai.parse_document available: {hasattr(bbq.ai, 'parse_document')}")

session = bpd.get_global_session()
bf_blocks = session.read_gbq_query(f"""
WITH ParsedDocs AS (
  SELECT
    REGEXP_EXTRACT(uri, r'[^/]+$') AS file_name,
    AI.PARSE_DOCUMENT(ref) AS parsed_doc
  FROM `{PROJECT_ID}.{DATASET_ID}.ai_parse_document_docs`
)
SELECT
  file_name,
  INT64(block.id) AS block_id,
  JSON_VALUE(block.type) AS block_type,
  INT64(block.page_number) AS page_number,
  CHAR_LENGTH(JSON_VALUE(block.content)) AS char_len
FROM ParsedDocs,
UNNEST(JSON_QUERY_ARRAY(parsed_doc.blocks)) AS block
ORDER BY file_name, block_id
""")
bf_blocks.to_pandas().head(10)
```
