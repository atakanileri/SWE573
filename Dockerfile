FROM python:3.12-slim

WORKDIR /app

# Dependencies first so a code-only change doesn't reinstall them.
COPY backend/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY backend /app/backend
COPY frontend /app/frontend

ENV PYTHONPATH=/app/backend
ENV DATABASE_URL=sqlite:////data/crafts.db
ENV SEED_DEMO_DATA=1

WORKDIR /app/backend

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
