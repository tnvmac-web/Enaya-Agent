# Enaya Agent Dockerfile
# Multi-stage build for smaller production image

# ============================================================
# Build Stage
# ============================================================
FROM python:3.11-slim as builder

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy dependency files
COPY pyproject.toml README.md ./

# Install package in development mode with all extras
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -e ".[dev]"

# ============================================================
# Runtime Stage
# ============================================================
FROM python:3.11-slim

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -r enaya && useradd -r -g enaya -d /home/enaya -s /bin/bash enaya && \
    mkdir -p /home/enaya && chown -R enaya:enaya /home/enaya

# Set working directory
WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy source code
COPY --chown=enaya:enaya src/ ./src/
COPY --chown=enaya:enaya pyproject.toml README.md ./

# Install the package
RUN pip install --no-cache-dir -e .

# Create directories for config and data
RUN mkdir -p /home/enaya/.enaya && chown -R enaya:enaya /home/enaya/.enaya

# Switch to non-root user
USER enaya
ENV HOME=/home/enaya
ENV ENAYA_HOME=/home/enaya/.enaya

# Expose ports
EXPOSE 8000 8080 3000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Default command
ENTRYPOINT ["enaya"]
CMD ["chat", "-q", "Hello"]