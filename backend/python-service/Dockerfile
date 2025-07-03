FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN pip install poetry
# Copy Poetry files
COPY pyproject.toml poetry.lock* ./

# Configure Poetry and install dependencies
RUN poetry config virtualenvs.create false \
    && poetry install

# Copy startup script first (since it changes less frequently)
COPY start-dev.sh .
RUN chmod +x start-dev.sh

# Copy source code (which changes most frequently)
COPY . .

# Expose port
EXPOSE 5000

#RUN CMD is in devcontainer.json
