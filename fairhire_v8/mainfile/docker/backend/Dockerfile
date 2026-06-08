# Multi-stage build for FastAPI backend
FROM python:3.11-slim AS builder

WORKDIR /app

# Install system dependencies needed for compiling packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy the custom requirements file
COPY docker/backend/requirements.docker.txt .

# Install dependencies into /root/.local
RUN pip install --no-cache-dir --user -r requirements.docker.txt

# --- Stage 2: Runtime ---
FROM python:3.11-slim AS runner

WORKDIR /app

# Install runtime dependencies (libpq is needed for psycopg2, curl for health checks)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy installed python packages from the builder stage
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

# Copy backend source files from build context root
COPY fairhire/api.py fairhire/audit_engine.py fairhire/report_generator.py fairhire/stripe_webhook.py ./

# Create non-root user and set permissions
RUN useradd -u 10001 -m appuser && chown -R appuser:appuser /app
USER appuser

# Expose port 8080
EXPOSE 8080

# Health check to ensure the backend is running
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:${PORT:-8080}/api/health || exit 1

# Start the application using Uvicorn
CMD ["sh", "-c", "uvicorn api:app --host 0.0.0.0 --port ${PORT:-8080} --workers 1 --timeout-keep-alive 30"]
