# Professional Automated Trading System
# Production-ready Docker setup with UV

# Base image with Python 3.11
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies and UV
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    && curl -LsSf https://astral.sh/uv/install.sh | sh \
    && rm -rf /var/lib/apt/lists/*

# Add uv to PATH
ENV PATH="/root/.cargo/bin:$PATH"

# Create app user (security best practice)
RUN useradd --create-home --shell /bin/bash app

# Copy pyproject.toml and uv.lock for dependency installation
COPY pyproject.toml uv.lock* ./

# Install Python dependencies using UV
RUN uv sync --frozen

# Copy application code
COPY src/ ./src/
COPY config.yaml ./
COPY alembic.ini ./
COPY alembic/ ./alembic/

# Create data directory for database
RUN mkdir -p /app/data && \
    mkdir -p /app/logs

# Set ownership
RUN chown -R app:app /app

# Switch to app user
USER app

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Health check using UV
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD uv run python -c "import requests; requests.get('http://localhost:8000/health')" || exit 1

# Expose port
EXPOSE 8000

# Command to run the application using UV
CMD ["uv", "run", "python", "src/main_automated.py"]
