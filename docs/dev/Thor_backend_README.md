# Thor Django Backend

A Django REST API backend for the Thor application, featuring Norse mythology-themed models and a comprehensive API.

## Features

- **Hero Management**: Create and manage Norse mythology heroes with power levels, realms, and weapons
- **Quest System**: Track quests assigned to heroes with difficulty levels and completion status
- **Artifact System**: Manage magical artifacts owned by heroes with rarity levels
- **REST API**: Full CRUD operations for all models via Django REST Framework
- **Admin Interface**: Django admin panel for easy data management
- **PostgreSQL Database**: Connected to PostgreSQL database via Docker

## Models

### Hero
- Name, title, description
- Power level (1-100)
- Realm (Asgard, Midgard, etc.)
- Weapon
- Timestamps

### Quest
- Title, description
- Assigned hero
- Difficulty level (Easy, Medium, Hard, Epic, Legendary)
- Completion status
- Reward
- Timestamps

### Artifact
- Name, description, power
- Rarity level (Common, Uncommon, Rare, Epic, Legendary)
- Owner (Hero)
- Timestamps

## API Endpoints

- `GET /api/` - API overview
- `GET /api/stats/` - Application statistics
- `GET /api/heroes/` - List all heroes
- `POST /api/heroes/` - Create a new hero
- `GET /api/heroes/{id}/` - Get hero details
- `PUT /api/heroes/{id}/` - Update hero
- `DELETE /api/heroes/{id}/` - Delete hero
- `GET /api/quests/` - List all quests
- `POST /api/quests/` - Create a new quest
- `GET /api/quests/{id}/` - Get quest details
- `PUT /api/quests/{id}/` - Update quest
- `DELETE /api/quests/{id}/` - Delete quest
- `GET /api/artifacts/` - List all artifacts
- `POST /api/artifacts/` - Create a new artifact
- `GET /api/artifacts/{id}/` - Get artifact details
- `PUT /api/artifacts/{id}/` - Update artifact
- `DELETE /api/artifacts/{id}/` - Delete artifact

## Setup Instructions

### Prerequisites
- Python 3.8+
- PostgreSQL (running in Docker)
- Virtual environment

### Installation

1. **Clone and navigate to the project:**
   ```bash
   cd thor-backend
   ```

2. **Create and activate virtual environment:**
   ```bash
   python -m venv venv
   .\venv\Scripts\Activate.ps1  # Windows
   # or
   source venv/bin/activate  # macOS/Linux
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables:**
   Create a `.env` file with:
   ```
   SECRET_KEY=your-secret-key
   DEBUG=True
   DB_NAME=thor_db
   DB_USER=thor_user
   DB_PASSWORD=thor_password
   DB_HOST=localhost
   DB_PORT=5433
   ```

5. **Start PostgreSQL container:**
   ```bash
   docker start thor_postgres
   ```

6. **Run migrations:**
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```

7. **Create superuser (optional):**
   ```bash
   python manage.py createsuperuser
   ```

8. **Start development server:**
   ```bash
   python manage.py runserver
   ```

## Usage

### Admin Interface
- Visit `http://127.0.0.1:8000/admin/`
- **Login credentials:**
  - Username: `admin`
  - Password: `Coco1464#`
  - Email: `admin@thor.com`
- Manage heroes, quests, and artifacts through the admin panel

### API Testing
- Visit `http://127.0.0.1:8000/api/` for API overview
- Use tools like Postman or curl to test endpoints
- All endpoints support filtering, searching, and ordering

### Example API Calls

**Create a Hero:**
```bash
curl -X POST http://127.0.0.1:8000/api/heroes/ \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Thor",
    "title": "God of Thunder",
    "description": "Wielder of Mjolnir",
    "power_level": 95,
    "realm": "Asgard",
    "weapon": "Mjolnir"
  }'
```

**Get All Heroes:**
```bash
curl http://127.0.0.1:8000/api/heroes/
```

## Database Configuration

The application is configured to use PostgreSQL running in Docker:
- Database: `thor_db`
- User: `thor_user`
- Password: `thor_password`
- Host: `localhost`
- Port: `5433`

## CORS Configuration

CORS is configured to allow requests from:
- `http://localhost:3000` (React development server)
- `http://localhost:5173` (Vite development server)

## Technologies Used

- Django 5.2.6
- Django REST Framework
- PostgreSQL
- django-cors-headers
- django-filter
- python-decouple

## Project Structure

```
thor-backend/
├── manage.py
├── requirements.txt
├── .env
├── thor_project/
│   ├── __init__.py
│   ├── settings.py
│   ├── urls.py
│   ├── wsgi.py
│   └── asgi.py
├── core/
│   ├── models.py
│   ├── admin.py
│   ├── migrations/
│   └── ...
└── api/
    ├── views.py
    ├── serializers.py
    ├── urls.py
    └── ...
```

## Next Steps

The backend is now ready for frontend integration. You can proceed with creating the React Vite frontend that will consume these APIs.