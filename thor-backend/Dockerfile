# Use Python 3.11 slim image for smaller size
FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Set work directory
WORKDIR /app

# Install system dependencies for PostgreSQL
RUN apt-get update && apt-get install -y \
    postgresql-client \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies (excluding Windows-only packages)
RUN pip install --no-cache-dir -r requirements.txt || true && \
    pip install --no-cache-dir \
    asgiref==3.9.1 \
    Django==5.2.6 \
    django-cors-headers==4.9.0 \
    django-filter==25.1 \
    djangorestframework==3.16.1 \
    psycopg2-binary==2.9.10 \
    python-decouple==3.8 \
    sqlparse==0.5.3 \
    tzdata==2025.2 \
    openpyxl==3.1.5 \
    pytz==2024.2 \
    redis==5.0.8 \
    requests>=2.32.3

# Copy project files
COPY . .

# Create directory for static files
RUN mkdir -p /app/staticfiles

# Collect static files (run during build)
RUN python manage.py collectstatic --noinput || echo "Static files collection skipped"

# Expose port 8000
EXPOSE 8000

# Run server without auto-migrations (run migrations manually)
CMD python manage.py runserver 0.0.0.0:8000
