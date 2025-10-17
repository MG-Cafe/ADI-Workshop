# Invoice Intelligence Backend

This FastAPI application is a production-grade replacement for the original Streamlit experience. It exposes REST APIs for invoice ingestion, analytics, and the conversational assistant.

## Features

- Upload PDF invoices and run them through Azure Document Intelligence (or a lightweight PDF fallback parser).
- Persist normalized invoice data and line items in SQLite via SQLModel.
- Expose analytics endpoints used by the web client for dashboards and charts.
- Provide a chat endpoint backed by Azure OpenAI or a deterministic rule-based fallback.
- Serve the front-end assets and templates for the web client.

## Getting started

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
uvicorn backend.app.main:app --reload
```

Create a `.env` file in the repository root (or export environment variables) with:

```
AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT="https://<resource-name>.cognitiveservices.azure.com/"
AZURE_DOCUMENT_INTELLIGENCE_KEY="<your-key>"
AZURE_OPENAI_ENDPOINT="https://<resource-name>.openai.azure.com/"
AZURE_OPENAI_API_KEY="<your-key>"
AZURE_OPENAI_DEPLOYMENT="<gpt-deployment-name>"
```

With no Azure credentials the application still works for text-based PDFs using the fallback parser and deterministic chat responses.

## Running tests

```bash
pytest backend/tests
```

The tests exercise the local PDF parser using the sample invoices already committed to the repository.
