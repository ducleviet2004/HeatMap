FROM python:3.12.8-slim-bookworm AS base

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY pyproject.toml alembic.ini ./
COPY app ./app
COPY migrations ./migrations
RUN pip install --no-cache-dir .

FROM base AS test
COPY tests ./tests
COPY scripts ./scripts
RUN pip install --no-cache-dir ".[dev]"
RUN ruff format --check . && ruff check . && mypy app && pytest

FROM base AS production
RUN useradd --create-home --uid 10001 appuser && chown -R appuser:appuser /app
USER appuser
EXPOSE 8000
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
