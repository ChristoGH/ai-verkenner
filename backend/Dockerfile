# AI Verkenner backend — local dev image (M2).
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install dependencies first (better layer caching), then the app.
COPY pyproject.toml README.md ./
COPY app ./app
RUN pip install .

EXPOSE 8000

# Default command; docker-compose overrides with --reload for dev. Binds all interfaces so the
# host-mapped port is reachable.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
