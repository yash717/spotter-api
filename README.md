# Spotter AI — ELD Trip Planner API

<p align="center">
  <strong>Django REST API for the Spotter AI ELD Trip Planner</strong>
</p>

---

## Overview

Backend API for **Spotter AI** — organizations, roles, invitations, fleet management, trips, HOS simulation, and ELD daily log generation. Implements FMCSA Hours of Service rules (70hr/8day, 11hr drive, 14hr window, 30min break, 10hr reset, fuel every 1,000 miles).

### Features

- **Auth** — JWT authentication, registration, login
- **Organizations** — Multi-tenant with roles (PLATFORM_ADMIN, ORG_ADMIN, DISPATCHER, DRIVER, FLEET_MANAGER)
- **Invitations** — JWT-signed invite links, accept flow
- **Trips** — Plan trips with geocoding, routing (OpenRouteService), HOS simulation
- **ELD Logs** — Daily log sheets, duty status segments
- **Fleet** — Vehicles, driver profiles, assignments

---

## Tech Stack

- **Framework:** Django 5, Django REST Framework
- **Auth:** JWT (Simple JWT)
- **Routing:** OpenRouteService (or Haversine fallback)
- **Geocoding:** OpenRouteService Pelias

---

## Getting Started

### Prerequisites

- Python 3.11+
- PostgreSQL (optional; SQLite for dev)

### Installation

```bash
# Clone the repository
git clone https://github.com/yash717/spotter-api.git
cd spotter-api

# Create and activate virtualenv
python3 -m venv venv
source venv/bin/activate   # Linux/macOS
# or: venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env: set SECRET_KEY, INVITATION_JWT_SECRET, ORS_API_KEY (optional)

# Run migrations
python manage.py migrate

# (Optional) Seed dev data
python manage.py seed_dev_data

# Run server
python manage.py runserver
```

- **API docs:** http://localhost:8000/api/docs/ (Swagger)
- **ReDoc:** http://localhost:8000/api/redoc/
- **Admin:** http://localhost:8000/admin/

### Environment Variables

| Variable | Description |
|----------|-------------|
| `SECRET_KEY` | Django secret key |
| `INVITATION_JWT_SECRET` | Separate secret for invitation tokens |
| `ORS_API_KEY` | OpenRouteService API key (for routing/geocoding) |
| `CORS_ALLOWED_ORIGINS` | Allowed frontend origins |
| `FRONTEND_URL` | Frontend base URL |

See `.env.example` for full list.

---

## API Endpoints

| Area | Endpoints |
|------|-----------|
| Auth | `/api/v1/auth/register/`, `/api/v1/auth/login/`, `/api/v1/auth/session/` |
| Trips | `/api/v1/trips/`, `/api/v1/trips/plan/`, `/api/v1/trips/{id}/` |
| Invitations | `/api/v1/invitations/`, `/api/v1/invitations/validate/`, `/api/v1/invitations/accept/` |
| Fleet | `/api/v1/vehicles/`, `/api/v1/profile/` |

---

## License

Private — Spotter AI Assessment
