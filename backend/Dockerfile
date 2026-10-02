FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY pyproject.toml ./
RUN pip install --no-cache-dir .
COPY alembic.ini ./
COPY alembic ./alembic
COPY app ./app
COPY scripts ./scripts
EXPOSE 8000
CMD ["sh", "-c", "python -m scripts.wait_for_db && alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
