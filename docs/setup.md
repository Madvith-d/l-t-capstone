# Setup

## Docker development

1. Copy `.env.example` to `.env`.
2. Start the already-installed host Ollama and verify `ollama list` contains `gemma4:e2b`.
3. Keep `LLM_PROVIDER=ollama`, `LLM_MODEL=gemma4:e2b`, and `OLLAMA_BASE_URL=http://host.docker.internal:11435`, then run `docker compose up --build`.
4. Open `http://localhost:3000`; API docs are at `http://localhost:8000/docs`.
5. Ingest the clearly labelled synthetic demo corpus:

```bash
docker compose exec backend python -m scripts.ingest \
  data/demo/DEMO-academic-regulations.txt \
  data/demo/DEMO-semester-four-syllabus.txt \
  --category demo --academic-year DEMO
```

Real use requires owner-approved college PDFs/TXT files via the Sources screen or `data/raw/`. Demo statements are fictional.

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
npm ci
npm run dev
```

For a backend running outside Docker, set `OLLAMA_BASE_URL=http://localhost:11434`. On Linux, Compose runs a small `socat` bridge from host port `11435` to the loopback-only Ollama port `11434`, then uses an explicit host-gateway mapping. This does not install Ollama or duplicate the model inside Docker. Override `OLLAMA_BRIDGE_PORT` if 11435 is occupied.

FastEmbed downloads `BAAI/bge-small-en-v1.5` once and Compose caches it in `embedding_cache`. Changing the embedding model changes the vector space. Rebuild existing stored vectors with `docker compose exec backend python -m scripts.reembed`; newly ingested documents automatically use the configured model.

## Validation

```bash
cd backend && pytest -q && ruff check app scripts tests
cd frontend && npm ci && npm run lint && npm run build

docker compose config
docker compose build
docker compose up -d
docker compose ps
docker compose logs --no-color
docker compose exec backend python -m scripts.smoke_pgvector
curl http://localhost:8000/health
```

## Docker troubleshooting

Compose uses the `app_network`; `postgres` is the database DNS name inside containers. To recreate stale containers:

```bash
docker compose down --remove-orphans
docker compose up --build
```

Override published host ports with `POSTGRES_PORT`, `BACKEND_PORT`, or `FRONTEND_PORT`; do not replace the container database hostname with `localhost`.
