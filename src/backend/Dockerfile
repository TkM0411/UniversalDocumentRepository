# ---- build stage ----
FROM python:3.11-slim AS builder

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# ---- runtime stage ----
FROM python:3.11-slim

ARG VERSION="1.0.0"
ARG BUILD_DATE

LABEL Product="UniversalDocumentRepositoryAPI"
LABEL Version=${VERSION}
LABEL BuildDate=${BUILD_DATE}
LABEL Maintainer="TkM"
LABEL Description="Universal Document Repository API"

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application source
COPY . .

# Non-root user for least-privilege execution
RUN adduser --disabled-password --gecos "" appuser \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 5000

# 4 workers; tune via GUNICORN_WORKERS env var if needed
CMD ["gunicorn", \
     "--bind", "0.0.0.0:5000", \
     "--workers", "4", \
     "--timeout", "120", \
     "--access-logfile", "-", \
     "--error-logfile", "-", \
     "app:create_app()"]
