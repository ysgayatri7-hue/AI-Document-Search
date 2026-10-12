FROM python:3.12-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 HF_HOME=/app/model-cache
WORKDIR /app
RUN useradd --create-home --uid 10001 appuser
COPY requirements.txt .
# Install the CPU wheel explicitly. Without this, newer PyTorch releases may
# pull hundreds of megabytes of CUDA packages into a CPU-only API container.
RUN pip install --no-cache-dir torch==2.5.1 --index-url https://download.pytorch.org/whl/cpu \
    && pip install --no-cache-dir -r requirements.txt
COPY scripts/cache_models.py ./scripts/cache_models.py
ARG PRELOAD_MODELS=true
RUN mkdir -p /app/model-cache \
    && if [ "$PRELOAD_MODELS" = "true" ]; then python scripts/cache_models.py; fi
COPY alembic.ini ./
COPY alembic ./alembic
COPY app ./app
RUN mkdir -p /app/uploads && chown -R appuser:appuser /app
USER appuser
EXPOSE 8000
CMD ["sh","-c","alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000 --proxy-headers --forwarded-allow-ips='*'"]

