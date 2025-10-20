# Thor Docker Deployment

## Quick Start

1. **Create your `.env` file** (copy from `.env.example`):
   ```powershell
   Copy-Item .env.example .env
   ```
   Then edit `.env` with your actual credentials.

2. **Build and start all services**:
   ```powershell
   docker-compose up -d --build
   ```

3. **Check status**:
   ```powershell
   docker-compose ps
   ```

4. **View logs**:
   ```powershell
   # All services
   docker-compose logs -f
   
   # Specific service
   docker-compose logs -f backend
   ```

## Services

- **PostgreSQL**: Port 5432 (Database)
- **Redis**: Port 6379 (Cache)
- **Django Backend**: Port 8000 (API)

## Common Commands

### Start services
```powershell
docker-compose up -d
```

### Stop services
```powershell
docker-compose down
```

### Restart a service
```powershell
docker-compose restart backend
```

### Run Django management commands
```powershell
# Create superuser
docker-compose exec backend python manage.py createsuperuser

# Make migrations
docker-compose exec backend python manage.py makemigrations

# Run migrations
docker-compose exec backend python manage.py migrate

# Django shell
docker-compose exec backend python manage.py shell
```

### Run scripts
```powershell
# Populate futures data
docker-compose exec backend python scripts/populate_futures_data.py

# Setup Schwab Live Data
docker-compose exec backend python scripts/setup_schwab_live_data.py
```

### Database access
```powershell
# PostgreSQL shell
docker-compose exec postgres psql -U thor_user -d thor_db

# Redis CLI
docker-compose exec redis redis-cli
```

### Clean rebuild
```powershell
# Stop and remove containers, networks, volumes
docker-compose down -v

# Rebuild and start
docker-compose up -d --build
```

## Development vs Production

### Development (Current Setup)
- `DEBUG=True` in `.env`
- Volume mounting for hot reload
- `runserver` for easy debugging

### Production Recommendations
- Set `DEBUG=False`
- Use `gunicorn` or `uwsgi` instead of `runserver`
- Add Nginx reverse proxy
- Use proper secrets management
- Enable SSL/TLS

## Troubleshooting

### Backend won't start
```powershell
# Check logs
docker-compose logs backend

# Verify database is ready
docker-compose exec postgres pg_isready -U thor_user
```

### Database connection issues
```powershell
# Check environment variables
docker-compose exec backend env | grep DATABASE

# Test connection manually
docker-compose exec backend python manage.py dbshell
```

### Clear everything and start fresh
```powershell
docker-compose down -v
docker-compose up -d --build
docker-compose exec backend python manage.py migrate
docker-compose exec backend python scripts/populate_futures_data.py
```
