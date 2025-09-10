# gunicorn.conf.py
import os

# Server socket
bind = f"0.0.0.0:{os.environ.get('PORT', '10000')}"

# Worker processes
workers = 1  # SocketIO requires single worker
worker_class = "gevent"  # Compatible with SocketIO and Python 3.13
worker_connections = 1000

# Logging
loglevel = "info"
accesslog = "-"
errorlog = "-"

# Process naming
proc_name = "tournamentpro"

# Timeout
timeout = 120
keepalive = 2

# Preload the application
preload_app = True

# Maximum requests per worker
max_requests = 1000
max_requests_jitter = 50
