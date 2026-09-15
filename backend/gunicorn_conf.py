import multiprocessing
import os

# Binding
host = os.getenv("HOST", "0.0.0.0")
port = os.getenv("PORT", "8000")
bind = f"{host}:{port}"

# Workers
workers_per_core = float(os.getenv("WORKERS_PER_CORE", "1"))
cores = multiprocessing.cpu_count()
default_web_concurrency = workers_per_core * cores
web_concurrency = int(os.getenv("WEB_CONCURRENCY", str(default_web_concurrency)))

# Start at least 2 workers if possible
workers = max(web_concurrency, 2)
worker_class = "uvicorn.workers.UvicornWorker"

# Logging
loglevel = os.getenv("LOG_LEVEL", "info")
accesslog = "-"
errorlog = "-"

# Timeouts
timeout = int(os.getenv("TIMEOUT", "120"))
keepalive = int(os.getenv("KEEP_ALIVE", "5"))
