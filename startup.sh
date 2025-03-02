#!/bin/bash

# Navigate to the app directory (Azure places your app in /home/site/wwwroot)
cd /home/site/wwwroot

# Ensure the script has execute permissions
chmod +x startup.sh

# Start Gunicorn with 4 workers, binding to port 8000 (Azure default)
gunicorn --workers=4 --bind=0.0.0.0:8000 app:app
