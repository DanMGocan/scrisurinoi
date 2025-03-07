#!/usr/bin/env python
"""
Local development server script.
Run this script to start the Flask development server locally.
"""

import os
from app import create_app

if __name__ == "__main__":
    # Load environment variables from .env file if python-dotenv is installed
    try:
        from dotenv import load_dotenv
        load_dotenv()
        print("Loaded environment variables from .env file")
    except ImportError:
        print("python-dotenv not installed. Using environment variables from system.")
    
    # Create the Flask application
    app = create_app()
    
    # Get port from environment variable or use default
    port = int(os.environ.get("PORT", 5000))
    
    # Run the development server
    app.run(host="0.0.0.0", port=port, debug=True)
