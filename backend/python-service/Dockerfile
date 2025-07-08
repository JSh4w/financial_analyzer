# Sets the base image for the container
FROM python:3.11-slim

# Sets the working directory for the container
WORKDIR /app

# Installs the necessary system dependencies for the container
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN pip install poetry
# Copy Poetry files that can be cached
COPY pyproject.toml poetry.lock* ./

# Configure Poetry and install dependencies
RUN poetry config virtualenvs.create false \
    && poetry install

# Copy source code (which changes most frequently)
# We want to copy items in stages such that the cache is used as much as possible
COPY . .

# Expose port
EXPOSE 5000

# Copy startup script first (since it changes less frequently)
COPY start-dev.sh .
RUN chmod +x start-dev.sh
#RUN CMD is in devcontainer.json
