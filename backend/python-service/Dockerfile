FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt

# Install development dependencies for hot reloading
RUN pip install uvicorn[standard] watchfiles

# Copy startup script first (since it changes less frequently)
COPY start-dev.sh .
RUN chmod +x start-dev.sh

# Copy source code (which changes most frequently)
COPY . .

# Expose port
EXPOSE 5000

# Use the script as the entry point
CMD ["./start-dev.sh"]