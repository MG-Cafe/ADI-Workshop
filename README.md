# Invoice Intelligence Web Application

This repository contains a production-ready web experience that replaces the original Streamlit prototype. It provides a FastAPI backend with persistent storage and a responsive web user interface that mirrors the Streamlit app’s functionality, including analytics and the conversational AI assistant.

## Repository layout

- `backend/` – FastAPI application, database models, services, API routers, static assets, and tests.
- `DocumentProcessing_Invoices/` – Sample invoices used for local development and automated tests.

## Running locally

1. Create a Python virtual environment and install dependencies:

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r backend/requirements.txt
   ```

2. Configure Azure credentials (optional but recommended for production parity):

   ```bash
   cp .env.sample .env  # edit values accordingly
   ```

3. Launch the backend:

   ```bash
   uvicorn backend.app.main:app --reload
   ```

4. Open `http://localhost:8000` in a browser to access the web interface.

With no Azure credentials the system will gracefully fall back to the built-in PDF parser (for text-based PDFs) and a deterministic chat assistant.

## Tests

Run the test suite with:

```bash
pytest backend/tests
```

The tests rely on the sample invoices that ship with the repository.
