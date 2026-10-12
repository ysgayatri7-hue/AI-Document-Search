# AI Document Search

Production-oriented AI document search and fact-checking assistant with page-level evidence, hybrid retrieval, citation validation, and claim verification.

![Python](https://img.shields.io/badge/Python-3.12-3776AB) ![React](https://img.shields.io/badge/React-TypeScript-149ECA) ![License](https://img.shields.io/badge/license-MIT-6656D9)

## What works

- Account registration/login with Argon2 password hashing and expiring JWTs.
- Owner-scoped PDF upload, signature/size validation, duplicate detection, deletion, retry, and real processing states.
- PyMuPDF extraction with page provenance and explicit scanned/unreadable-PDF failures. OCR is not claimed.
- Overlapping chunks, Sentence Transformer embeddings, Qdrant persistence, BM25, reciprocal-rank fusion, and cross-encoder reranking.
- Offline deterministic embedding/reranking fallbacks when model weights are unavailable.
- An honest no-key extractive answer mode. Provider settings are reserved for a future adapter and do not enable external generation today.
- Numbered, validated citations with filename, page, and expandable source excerpts.
- Claim statuses: supported, partially supported, contradicted, and unsupported.
- Injection heuristics, untrusted-document boundaries, output redaction, request validation, rate limiting, strict ownership enforcement, and privacy-conscious audit events.
- Responsive premium UI with light/dark themes, accessible controls, real empty states, feedback, history, and live analytics.
- Reproducible synthetic pipeline evaluation (explicitly not a benchmark), tests, migration, Docker Compose, and CI.

## Quick start with Docker

Requirements: Docker Desktop with Compose.

```bash
cp .env.example .env
# Replace SECRET_KEY and POSTGRES_PASSWORD before production use.
docker compose up --build
```

Open <http://localhost:8080>. The Compose stack keeps PostgreSQL, Qdrant, and the API on its private network; only the Nginx frontend is published. In local development, FastAPI documentation is available at <http://localhost:8000/docs>.

The first build downloads the public embedding and cross-encoder weights and can be large; no API key is required. For an offline fallback-only image, set `PRELOAD_MODELS=false`. If weights are unavailable, AI Document Search uses deterministic local fallbacks and records the active backends in content-free audit metadata. Answers remain labelled `extractive`.

## Local development

### Backend

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
source .venv/bin/activate
pip install -r backend/requirements-dev.txt
cp .env.example backend/.env
# For zero-config development set DATABASE_URL=sqlite:///./ai_document_search.db and QDRANT_URL=
cd backend
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
corepack enable
pnpm install --frozen-lockfile
pnpm dev
```

Open <http://localhost:5173>. Vite proxies `/api` to port 8000. For a remote API, set `VITE_API_URL` before building.

Local development does not download retrieval weights automatically. Run `python backend/scripts/cache_models.py` once while online to enable the real Sentence Transformer and cross-encoder; otherwise the UI and audit metadata disclose the deterministic fallbacks.

Windows PowerShell equivalents from the repository root:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r backend\requirements-dev.txt
Copy-Item .env.example backend\.env
# In backend\.env, use DATABASE_URL=sqlite:///./ai_document_search.db and leave QDRANT_URL blank for local-only development.
Set-Location backend
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

Open a second PowerShell terminal in the repository root:

```powershell
Set-Location frontend
corepack enable
pnpm install --frozen-lockfile
pnpm dev
```

## Tests and quality checks

```bash
python -m pytest
python -m ruff check backend
cd frontend && pnpm lint && pnpm test && pnpm build
cd .. && python scripts/evaluate.py
```

Tests cover extraction, chunk/page metadata, ranking fusion, verification, citation validation, authentication, invalid uploads, prompt injection, hostile document content, API errors, and cross-user access. External generation is absent from this release and is not simulated in tests.

## Configuration

All configuration is environment based; see `.env.example`. Important settings:

| Variable | Purpose |
| --- | --- |
| `SECRET_KEY` | JWT signing secret; use 32+ random bytes in production |
| `DATABASE_URL` | PostgreSQL production URL or SQLite development URL |
| `QDRANT_URL` | Qdrant endpoint; blank enables local vector fallback |
| `QDRANT_COLLECTION` | Base collection name; the app adds the embedding dimension to prevent model-version conflicts |
| `MAX_UPLOAD_MB` | Server-enforced PDF limit |
| `CHUNK_SIZE`, `CHUNK_OVERLAP` | Passage boundaries |
| `EMBEDDING_MODEL`, `RERANKER_MODEL` | Retrieval model identifiers |
| `PRELOAD_MODELS` | Download public retrieval weights during Docker build (default `true`) |
| `MINIMUM_RELEVANCE_SCORE` | Evidence threshold below which the app declines to answer |
| `MAX_PDF_PAGES`, `MAX_PDF_TEXT_CHARS` | Extraction resource limits |
| `LLM_PROVIDER` | Must remain `extractive` in this release |
| `LLM_API_KEY`, `LLM_BASE_URL`, `LLM_MODEL` | Reserved; no external provider adapter is implemented yet |

No secrets belong in Git. The app starts without an API key; it does not pretend that extractive output came from an LLM.

## API

FastAPI provides interactive OpenAPI docs at `/docs`. Implemented routes:

- `POST /api/auth/register`, `POST /api/auth/login`, `GET /api/auth/me`
- `POST /api/documents`, `GET /api/documents`, `GET/DELETE /api/documents/{id}`, `GET /api/documents/{id}/content`, `POST /api/documents/{id}/retry`
- `POST /api/query`, `GET /api/query/{id}`, `GET /api/history`, `POST /api/feedback`
- `GET /api/analytics/overview`, `GET /api/analytics/verification`, `GET /api/health`

All resource endpoints validate the authenticated owner in PostgreSQL. Client-supplied IDs and vector metadata are never trusted as authorization.

## Evaluation

`python scripts/evaluate.py` writes `data/evaluation/results.json`. The included dataset is deliberately small and synthetic; its results validate wiring only. Retrieval and verification metrics remain `null` until labelled examples exist. Add human-reviewed relevance and entailment labels before treating results as performance evidence.

Supported calculations include Recall@K, Precision@K, MRR, binary precision/recall/F1, false-positive rate, median, and p95 latency. The schema reserves unmeasured token usage and estimated cost rather than inventing values.

## Repository map

```text
backend/app/       API, models, ingestion, retrieval, verification, guardrails
backend/alembic/   database migrations
backend/tests/     unit, API, authorization, and adversarial tests
frontend/src/      responsive React application and typed API client
data/evaluation/   labelled sample and generated results
scripts/           evaluation entry point
docs/              architecture and production deployment guidance
.github/workflows/ CI for backend and frontend
```

See [Architecture](docs/ARCHITECTURE.md), [Engineering audit](docs/AUDIT.md), [Deployment](docs/DEPLOYMENT.md), and [Security](SECURITY.md).

## Important limitations

- Automated claim verification can be wrong; inspect the cited passage.
- Scanned PDFs require OCR, which is intentionally not implemented or claimed.
- Heuristic injection detection is only one layer; deterministic ownership and policy controls remain authoritative.
- The in-process rate limiter is appropriate for a single instance. Use a shared production limiter when scaling horizontally.
- In-process background ingestion is not durable: an API restart can interrupt a job. Use a persistent queue/worker before horizontal scaling.
- Prompt-injection detection and numeric redaction are narrow defense-in-depth controls, not proof that arbitrary documents are safe.
- Uploaded PDFs are structurally constrained, but no antivirus or content-disarm service is included.
- JWTs are stored in browser local storage; a successful same-origin XSS could steal a token. A hardened deployment should use an HttpOnly cookie/BFF design and a strict CSP with nonces.

## License

MIT

