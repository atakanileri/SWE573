FROM python:3.12-slim

WORKDIR /app

# Dependencies first so a code-only change doesn't reinstall them.
COPY backend/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY backend /app/backend
COPY frontend /app/frontend

ENV PYTHONPATH=/app/backend
# Compose points this at the volume. Render replaces it with the Postgres URL.
ENV DATABASE_URL=sqlite:////data/crafts.db
ENV SEED_DEMO_DATA=1

WORKDIR /app/backend

EXPOSE 8000

# Render sets PORT (10000 unless the service changes it). Locally it is
# unset, so the server listens on 8000. exec makes uvicorn the main process
# so a stop signal reaches it.
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
