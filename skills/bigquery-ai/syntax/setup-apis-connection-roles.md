# Setup: APIs, connection, roles

> **Source:** [`bigquery-ai/reference/cloud-ai-service-models.md#setup-apis-connection-roles`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ai/reference/cloud-ai-service-models.md#setup-apis-connection-roles)

All five run through a **Cloud Resource connection**. The connection's auto-provisioned service account — not your user account — is the identity that calls the service and reads Cloud Storage.

**The APIs to enable**, beyond `bigquery.googleapis.com` and `bigqueryconnection.googleapis.com`:

| Function | Service API | Also needs |
|---|---|---|
| `ML.TRANSLATE` | `translate.googleapis.com` | — |
| `ML.UNDERSTAND_TEXT` | `language.googleapis.com` | — |
| `ML.ANNOTATE_IMAGE` | `vision.googleapis.com` | `storage.googleapis.com` |
| `ML.TRANSCRIBE` | `speech.googleapis.com` | `storage.googleapis.com` |
| `ML.PROCESS_DOCUMENT` | `documentai.googleapis.com` | `storage.googleapis.com` |

**The roles to grant the connection's service account**, at project level:

| Role | `TRANSLATE` | `UNDERSTAND_TEXT` | `ANNOTATE_IMAGE` | `TRANSCRIBE` | `PROCESS_DOCUMENT` |
|---|---|---|---|---|---|
| `roles/serviceusage.serviceUsageConsumer` | ✅ | ✅ | ✅ | ✅ | ✅ |
| `roles/bigquery.connectionUser` | ✅ | ✅ | ✅ | ✅ | ✅ |
| `roles/storage.objectViewer` (object tables) | — | — | ✅ | ✅ | ✅ |
| Service-specific role | `roles/cloudtranslate.user` | *none exists* | *none exists* | `roles/speech.client` | `roles/documentai.apiUser` + `roles/documentai.viewer` |
| `roles/aiplatform.user` | comparison examples only | comparison examples only | comparison examples only | comparison examples only | comparison examples only |

Three things this table is for:

- **The service-specific role is not uniform, and its absence is not an oversight.** Cloud Vision and Cloud Natural Language have no predefined IAM role — `serviceusage.services.use` is the permission that gates them, so their column stops at the BigQuery-side rows. Translation and Speech-to-Text each add one; Document AI adds two. Copying one member's setup to another either over-grants or fails at call time.
- **`roles/serviceusage.serviceUsageConsumer` is the one people miss.** Without it every call fails, no matter which service. The `ML.TRANSLATE` notebook shows the exact message, which names the missing role — more than most IAM failures give you, but it arrives at call time.
- **`roles/aiplatform.user` is not part of any of these functions.** Each notebook ends by running an `AI.*` function over the same rows for comparison, and *that* is what needs it. A deployment that only calls the Cloud AI service model can leave it off.

**`CREATE MODEL` succeeding tells you nothing about permissions.** Model creation does not contact the service, so it completes happily against a connection that cannot call anything. The first failure arrives at call time.

**Grants do not take effect instantly.** A freshly granted binding can take a minute to become usable. Each of the four notebooks on this page ends its setup with a probe on the smallest possible input, in a wait loop, so the first real example runs against a connection that has been shown to work — worth copying into any script that creates the connection and then uses it.

See the [Setup Reference](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ai/setup) for connection creation, and each notebook's Setup section for a runnable, idempotent version that also prints which roles it granted.

---
