# Agentic RAG

Self-correcting Retrieval-Augmented Generation over a local legal-document corpus. The backend uses FastAPI, LangGraph, Groq, Sentence Transformers, and Qdrant. The frontend is a Vite + React app that shows the answer, retrieved chunks, and reasoning trace.

## Repo Layout

- `backend/`: API, ingestion, retrieval, LangGraph pipeline, experiments
- `frontend/`: React client
- `backend/data/`: local PDF/text corpus

The default local workflow assumes your private source documents stay in `backend/data/` on your machine and are not committed to git.

## Backend Prereqs

- Python 3.13 recommended
- Qdrant instance and API key
- Groq API key

## Backend Setup

From the repo root:

```powershell
py -3.13 -m venv venv313
.\venv313\Scripts\python.exe -m pip install -r backend\requirements.txt
Copy-Item backend\.env.example backend\.env
```

Fill in `backend/.env` with your real `GROQ_API_KEY`, `QDRANT_URL`, and `QDRANT_API_KEY`.

## Ingest Documents

From the repo root:

```powershell
.\venv313\Scripts\python.exe backend\ingest.py --dry-run
.\venv313\Scripts\python.exe backend\ingest.py
```

## Run Backend

From the repo root:

```powershell
.\venv313\Scripts\python.exe -m uvicorn backend.main:app --reload
```

Or from `backend/`:

```powershell
..\venv313\Scripts\python.exe -m uvicorn main:app --reload
```

Backend URLs:

- `http://127.0.0.1:8000/health`
- `http://127.0.0.1:8000/docs`

## Frontend Setup

From `frontend/`:

```powershell
Copy-Item .env.example .env.local
npm.cmd install
npm.cmd run dev
```

Frontend URL:

- `http://127.0.0.1:5173`

The default frontend env points to `http://127.0.0.1:8000`.

## Local Run Order

1. Start the backend.
2. Start the frontend in a separate terminal.
3. Open the frontend and test end-to-end queries.

## Validation Checklist

- Ask a document-grounded query.
- Ask a greeting like `hi` and confirm it routes direct.
- Ask the same question twice and confirm cache behavior.
- Confirm retrieved chunks and reasoning trace render in the UI.

## Deployment Notes

### Backend on Railway

The backend includes [`backend/Dockerfile`](/d:/Recurse_Rag/agentic-rag/backend/Dockerfile) and [`backend/railway.toml`](/d:/Recurse_Rag/agentic-rag/backend/railway.toml).

Set these Railway variables:

- `GROQ_API_KEY`
- `QDRANT_URL`
- `QDRANT_API_KEY`
- `COLLECTION_NAME`
- `GROQ_MODEL`
- `EMBEDDING_MODEL`
- `TOP_K`
- `MAX_RETRIES`
- `CACHE_THRESHOLD`
- `CACHE_MAX_SIZE`
- `ALLOWED_ORIGINS`

Set `ALLOWED_ORIGINS` to include your deployed frontend origin.

### Frontend on Vercel

Set:

- `VITE_API_URL=https://your-backend-domain`

Build command:

```bash
npm run build
```

Output directory:

```text
dist
```

## Known Notes

- The first embedding-model load can take time on a fresh machine.
- If PowerShell blocks `Activate.ps1`, run Python directly from `venv313\Scripts\python.exe` instead of activating the venv.
- If the browser shows `failed to fetch`, first verify backend health and CORS origins.
