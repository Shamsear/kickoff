#!/usr/bin/env python3
"""
Production startup script for Render deployment
"""
import os
from app import create_app

# Create the Flask app and SocketIO instance
app, socketio = create_app()

# For Gunicorn, we need to expose the WSGI application
application = app

if __name__ == "__main__":
    # This won't be used in production, but good for local testing
    port = int(os.environ.get("PORT", 10000))
    socketio.run(app, host='0.0.0.0', port=port, debug=False)
