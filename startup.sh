#!/bin/bash

# This script is used to start the application in Google Cloud Run or App Engine

# Get the PORT environment variable or use 8080 as default
PORT=${PORT:-8080}

# Ensure the script has execute permissions
chmod +x startup.sh

# Run database migrations if needed (uncomment if you want to run migrations on startup)
# python db_migrate.py

# Start Gunicorn with appropriate settings for Cloud Run
# - workers: 1-2 per CPU core
# - threads: 8 per worker for better concurrency
# - timeout: 0 to disable timeouts (Cloud Run has its own timeout mechanism)
# - access-logfile: - to log to stdout
# - error-logfile: - to log to stderr
gunicorn --workers=1 --threads=8 --timeout=0 --bind=0.0.0.0:${PORT} \
  --access-logfile=- --error-logfile=- \
  "app:create_app()"
