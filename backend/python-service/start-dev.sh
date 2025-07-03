#!/bin/bash
# /app/start-dev.sh

echo "Starting development server..."
# Add any pre-startup tasks here (database migrations, etc.)

echo "http://localhost:5000/apple"
# Start server with hot reloading
uvicorn app.main_test:app --host 0.0.0.0 --port 5000 --reload --reload-delay 0.2