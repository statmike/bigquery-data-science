# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 0.7.x   | :white_check_mark: |

## Reporting a Vulnerability

Please **do not** report security vulnerabilities or exposed credentials through public GitHub issues, discussions, or pull requests.

Instead, report vulnerabilities privately through **[GitHub Security Advisories](https://github.com/statmike/bigquery-data-science/security/advisories/new)** on this repository. Please include:

1. A description of the issue and its potential impact.
2. The affected module (`src/bigquery_data_science/...`), skill (`skills/...`), or notebook/SQL path (`bigquery-ml/...`, `bigquery-ai/...`).
3. Minimal steps to reproduce or verify the issue.

We will acknowledge receipt within 5 business days and coordinate a fix and disclosure timeline with you.

---

## Credential & Authentication Policy

Workflows, notebooks, and CLI tools in `bigquery-data-science` are designed to run on Google Cloud without static secrets:

1. **No service account keys:** Notebooks and scripts authenticate exclusively via short-lived [Application Default Credentials (ADC)](https://cloud.google.com/docs/authentication/provide-credentials-adc) (`gcloud auth application-default login` locally, or attached IAM service accounts in Vertex AI Workbench, Colab Enterprise, BigQuery Studio, Agent Engine, Cloud Run, and Composer).
2. **Never commit credentials:** Service account JSON key files (`*-key.json`, `*_key.json`, `*.json.key`, `service-account*.json`, `*credentials*.json`) and local secret overrides (`.env`, `.env.*`) are blocked by [`.gitignore`](.gitignore) and must never be committed to the repository.
