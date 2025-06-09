# Dockerfile for Intelligent Drawing Generator
# Phase 6: Docker packaging with web API

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    fonts-liberation \
    fonts-dejavu-core \
    libcairo2-dev \
    libgirepository1.0-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create output directories
RUN mkdir -p /app/out /app/dataset_output /app/regression_results

# Set up symbol library
RUN python build_symbol_library.py

# Expose port for web API
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health')" || exit 1

# Default command
CMD ["python", "web_api.py"]