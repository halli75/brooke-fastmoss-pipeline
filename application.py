#!/usr/bin/env python3
"""
WSGI application entry point for deployment
"""
import os
import sys

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import the FastAPI app - try simple_app first, fall back to api_server
try:
    from simple_app import app as application
except ImportError:
    from api_server import app as application

# For Gunicorn
app = application

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
