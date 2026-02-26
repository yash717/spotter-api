# Spotter AI - Setup Instructions

## Virtual Environment Setup ✅

### 1. Virtual Environment Location
```
spotter-api/venv/
```

### 2. Activate Virtual Environment

**Linux/macOS:**
```bash
cd /home/hc-user/Videos/spotter-api
source venv/bin/activate
```

**Or use direct path (no activation needed):**
```bash
/home/hc-user/Videos/spotter-api/venv/bin/python manage.py <command>
/home/hc-user/Videos/spotter-api/venv/bin/pip <command>
```

### 3. Install Dependencies

All dependencies are frozen in `requirements.txt` with exact versions:

```bash
# Activate venv first, then:
pip install -r requirements.txt

# Or without activation:
venv/bin/pip install -r requirements.txt
```

**Total packages:** 29 (including dependencies)

**Main packages:**
- Django 6.0.2
- djangorestframework 3.16.1
- djangorestframework-simplejwt 5.5.1
- django-cors-headers 4.9.0
- django-ratelimit 4.1.0
- django-filter 25.2
- drf-spectacular 0.29.0
- django-jazzmin 3.0.2
- psycopg2-binary 2.9.11
- PyJWT 2.11.0
- python-decouple 3.8
- requests 2.32.5
- gunicorn 25.1.0

## Running the Application

### 1. Environment Configuration

Copy `.env.example` to `.env` and configure:

```bash
cp .env.example .env
```

**Required variables:**
```env
SECRET_KEY=your-secret-key
INVITATION_JWT_SECRET=your-invitation-secret
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
FRONTEND_URL=http://localhost:3000
```

**Email (Brevo SMTP - already configured):**
```env
SMTP_HOST=smtp-relay.brevo.com
SMTP_PORT=587
SMTP_USER=931fc0002@smtp-brevo.com
SMTP_PASS=xsmtpsib-ae968dbfbe313c59947966b7c0974bb025413705aca2a26bed9ee5ca03281dc8-eFmUsCjsjpXRfjbW
SMTP_FROM_EMAIL=dubbalwaryash@gmail.com
EMAIL_FROM=dubbalwaryash@gmail.com
```

### 2. Database Setup

```bash
# Run migrations
python manage.py migrate

# (Optional) Create superuser
python manage.py createsuperuser

# (Optional) Seed development data (25 users, 2 orgs, vehicles, trips)
python manage.py seed_dev_data
```

### 3. Start Development Server

```bash
# Activate venv
source venv/bin/activate

# Run server
python manage.py runserver

# Or without activation:
venv/bin/python manage.py runserver
```

**Access points:**
- API Docs (Swagger): http://localhost:8000/api/docs/
- ReDoc: http://localhost:8000/api/redoc/
- Admin Panel: http://localhost:8000/admin/
- API Base: http://localhost:8000/api/v1/

### 4. Verify Installation

```bash
# Django system check
python manage.py check

# Test database connection
python manage.py migrate --check

# Run tests (if available)
python manage.py test
```

## Development Workflow

### Adding New Dependencies

```bash
# Activate venv
source venv/bin/activate

# Install package
pip install package-name

# Update requirements.txt
pip freeze > requirements.txt
```

### Database Migrations

```bash
# Create migrations after model changes
python manage.py makemigrations

# Apply migrations
python manage.py migrate

# Check migration status
python manage.py showmigrations
```

### Code Quality

```bash
# Django check (security warnings)
python manage.py check --deploy

# Schema generation (test Swagger/OpenAPI)
python manage.py spectacular --file schema.yml
```

## Production Deployment

### 1. Environment Variables

Set in production environment:
- `DEBUG=False`
- Strong `SECRET_KEY` and `INVITATION_JWT_SECRET`
- Database URL (PostgreSQL recommended)
- Allowed hosts
- SMTP credentials (Brevo or SendGrid)

### 2. Database

```bash
# Use PostgreSQL in production
DATABASE_URL=postgres://user:pass@host:5432/dbname
```

### 3. Static Files

```bash
# Collect static files
python manage.py collectstatic --no-input
```

### 4. Run with Gunicorn

```bash
# Gunicorn is already installed
gunicorn eld_backend.wsgi:application \
  --bind 0.0.0.0:8000 \
  --workers 4 \
  --timeout 120
```

## Troubleshooting

### ImportError: No module named 'django'

Activate virtual environment first:
```bash
source venv/bin/activate
```

Or use full path:
```bash
venv/bin/python manage.py <command>
```

### Migration Errors

Reset migrations (development only):
```bash
python manage.py migrate --fake-initial
```

### Email Not Sending

Check SMTP credentials in `.env`:
- Verify `SMTP_USER` and `SMTP_PASS`
- Check `SMTP_FROM_EMAIL` is valid
- In development, emails log to console by default (unless SMTP vars are set)

## Quick Reference

| Command | Description |
|---------|-------------|
| `python manage.py runserver` | Start dev server |
| `python manage.py migrate` | Run migrations |
| `python manage.py makemigrations` | Create migrations |
| `python manage.py createsuperuser` | Create admin user |
| `python manage.py seed_dev_data` | Seed test data |
| `python manage.py shell` | Django shell |
| `python manage.py check` | System check |
| `pip freeze > requirements.txt` | Update requirements |

## Next Steps

1. ✅ Virtual environment created and activated
2. ✅ All dependencies installed (29 packages)
3. ✅ Requirements frozen to `requirements.txt`
4. ✅ Application tested and running
5. ✅ Email templates configured with Brevo SMTP

**You're all set! Start the server and begin development.**

```bash
source venv/bin/activate
python manage.py runserver
# Visit http://localhost:8000/api/docs/
```
