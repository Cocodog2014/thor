FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1

# All project files (both backend & frontend, .env) will live under /app
WORKDIR /app

# Install system deps (psycopg2 etc.)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev && \
    rm -rf /var/lib/apt/lists/*

# Copy only requirements first (for better layer caching)
# Host path: A:\Thor\thor-backend\requirements.txt
COPY thor-backend/requirements.txt ./thor-backend/requirements.txt
RUN pip install --no-cache-dir -r thor-backend/requirements.txt

# Copy the whole repo (includes .env, thor-backend, thor-frontend, etc.)
COPY . .

# Now work inside the backend folder
WORKDIR /app/thor-backend

# Run Django via Gunicorn (this uses your existing wsgi.py)
CMD ["gunicorn", "thor_project.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "4", "--timeout", "120"]
