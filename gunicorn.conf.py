"""
Gunicorn configuration for production deployment
"""

import multiprocessing
import os

# Server Socket
bind = "0.0.0.0:8000"
backlog = 2048

# Worker Processes
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "sync"
worker_connections = 1000
max_requests = 1000
max_requests_jitter = 100
timeout = 30
keepalive = 2

# Restart workers after this many requests, to help prevent memory leaks
max_requests = 1000
max_requests_jitter = 50

# Preload application code before forking worker processes
preload_app = True

# Restart workers when code changes (development only)
reload = False

# The maximum number of pending connections
backlog = 2048

# Logging
loglevel = "info"
accesslog = "/var/log/scholarship_portal/gunicorn_access.log"
errorlog = "/var/log/scholarship_portal/gunicorn_error.log"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Process naming
proc_name = "scholarship_portal"

# Server mechanics
daemon = False
pidfile = "/tmp/gunicorn.pid"
user = "appuser"
group = "appgroup"
tmp_upload_dir = None

# SSL
keyfile = None
certfile = None

# Worker temp directory
worker_tmp_dir = "/dev/shm"

# Worker timeout
timeout = 120
graceful_timeout = 30

# Security
limit_request_line = 4094
limit_request_fields = 100
limit_request_field_size = 8190

# Performance tuning
worker_class = "sync"  # or "gevent" for async workloads
sendfile = True

# Environment variables
raw_env = [
    'DJANGO_SETTINGS_MODULE=scholarship_portal.settings.production',
]

# Hooks
def on_starting(server):
    """Called just before the master process is initialized"""
    server.log.info("Starting Scholarship Portal server...")

def on_reload(server):
    """Called to recycle workers during a reload via SIGHUP"""
    server.log.info("Reloading Scholarship Portal server...")

def when_ready(server):
    """Called just after the server is started"""
    server.log.info("Scholarship Portal server is ready. Listening on: %s", server.address)

def worker_int(worker):
    """Called just after a worker exited on SIGINT or SIGQUIT"""
    worker.log.info("Worker received INT or QUIT signal")

def pre_fork(server, worker):
    """Called just before a worker is forked"""
    server.log.info("Worker spawned (pid: %s)", worker.pid)

def post_fork(server, worker):
    """Called just after a worker has been forked"""
    server.log.info("Worker spawned (pid: %s)", worker.pid)

def post_worker_init(worker):
    """Called just after a worker has initialized the application"""
    worker.log.info("Worker initialized (pid: %s)", worker.pid)

def worker_abort(worker):
    """Called when a worker received the SIGABRT signal"""
    worker.log.info("Worker received SIGABRT signal (pid: %s)", worker.pid)

# Custom Application
def application(environ, start_response):
    """WSGI application"""
    from scholarship_portal.wsgi import application as django_app
    return django_app(environ, start_response)
