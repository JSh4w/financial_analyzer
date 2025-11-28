#!/bin/bash
# /app/start-dev.sh

echo "Starting development server..."
# Add any pre-startup tasks here (database migrations, etc.)

# Start server with hot reloading
  poetry run uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload --log-level info --timeout-graceful-shutdown=5 #--no-access-log