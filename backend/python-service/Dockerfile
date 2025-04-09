FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install development dependencies for hot reloading
RUN pip install --no-cache-dir uvicorn[standard] watchfiles

# Copy source code
COPY . .

# Expose port
EXPOSE 5000

# Use ARG to set a build-time variable
ARG entry_point=main
ENV ENTRY_POINT=${entry_point}

# CMD uses the environment variable
CMD uvicorn app.${ENTRY_POINT}:app --host 0.0.0.0 --port 5000 --reload