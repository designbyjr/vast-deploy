# Multi-stage build for secure whisper ASR service
FROM python:3.11-slim-bookworm AS base

# Security: Create non-root user
RUN groupadd -r whisper && useradd -r -g whisper whisper

# Install system dependencies and security updates
RUN apt-get update && apt-get install -y \
    --no-install-recommends \
    curl \
    ca-certificates \
    openssl \
    build-essential \
    && apt-get upgrade -y \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Create app directory structure
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt ./

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip setuptools wheel \
    && pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

# Create necessary directories with proper permissions
RUN mkdir -p /app/certs /app/logs /app/temp \
    && chown -R whisper:whisper /app \
    && chmod 755 /app/certs /app/logs /app/temp

# Security: Switch to non-root user
USER whisper

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f -k https://localhost:9443/health || curl -f http://localhost:9443/health || exit 1

# Expose HTTPS port only
EXPOSE 9443

# Set environment variables for production
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV TLS_ENABLED=true
ENV TLS_AUTO_GENERATE=true
ENV REDIS_AUTH_ENABLED=false

# Start the secure service
CMD ["python", "run.py"]
