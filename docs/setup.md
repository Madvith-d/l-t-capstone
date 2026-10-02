# Setup

## Local services

1. Copy `.env.example` to `.env`.
2. Run `docker compose up --build`.
3. Open `http://localhost:3000`; API docs are at `http://localhost:8000/docs`.

## Native development

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -e '.[dev]'
alembic upgrade head
uvicorn app.main:app --reload
```

```bash
cd frontend
npm install
npm run dev
```

Set `GEMINI_API_KEY` in `.env` for generation. The default model is `gemini-2.5-flash-lite`. Embeddings run locally with FastEmbed and `sentence-transformers/all-MiniLM-L6-v2`; the ONNX model is downloaded on first use and cached in the Docker volume `embedding_cache`. The `local` provider remains available only as a deterministic test/offline fallback.

Changing `EMBEDDING_MODEL` changes the vector space. Re-run ingestion after a model change; ingestion detects the stored model marker and replaces stale chunks instead of mixing incompatible vectors.

## Docker troubleshooting

Compose connects all services to the explicit `app_network`; `postgres` is the database DNS alias inside that network. If containers from an older Compose definition are still present, recreate the stack:

```bash
docker compose down --remove-orphans
docker compose up --build
```

If host ports are already occupied, override only the published ports (service-to-service URLs remain unchanged):

```bash
POSTGRES_PORT=55432 FRONTEND_PORT=3300 docker compose up --build
```

Do not replace `postgres` with `localhost` in the backend container's `DATABASE_URL`; inside a container, `localhost` refers to that container itself. The Next.js standalone container explicitly binds to `0.0.0.0:3000`; do not remove its `HOSTNAME` override, because Docker otherwise supplies a container ID that Next.js may try to resolve as a network hostname.
