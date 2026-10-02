# ── Stage 1: Build ──────────────────────────────────────────────────────────
FROM python:3.12-alpine AS builder

WORKDIR /build
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip setuptools && \
    pip install --no-cache-dir --prefix=/install -r requirements.txt

# ── Stage 2: Runtime ────────────────────────────────────────────────────────
FROM python:3.12-alpine

LABEL maintainer="vehicle-rental-team"
LABEL version="1.0.0"
LABEL description="Vehicle Rental System API"

# Security: remove build tools/package manager from runtime and create non-root user
RUN python -m pip uninstall -y pip setuptools 2>/dev/null || true && \
    rm -rf /root/.cache /usr/local/lib/python3.12/ensurepip && \
    addgroup -S appuser && adduser -S -G appuser -h /app -s /sbin/nologin appuser

WORKDIR /app

# Copy installed dependencies from builder stage
COPY --from=builder /install /usr/local

# Copy application code
COPY app ./app

# Security: restrict file permissions
RUN chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
