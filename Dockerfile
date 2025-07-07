# Professional Automated Trading System
# Production-ready Docker setup

# Base image with Python 3.11
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Create app user (security best practice)
RUN useradd --create-home --shell /bin/bash app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

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

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health')" || exit 1

# Expose port
EXPOSE 8000

# Command to run the application
CMD ["python", "-m", "src.main_automated"]
