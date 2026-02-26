# Spotter AI - Recent Changes

## 1. Brevo Email Integration ✅

**Added to `.env`:**
```env
SMTP_HOST=smtp-relay.brevo.com
SMTP_PORT=587
SMTP_USER=931fc0002@smtp-brevo.com
SMTP_PASS=xsmtpsib-ae968dbfbe313c59947966b7c0974bb025413705aca2a26bed9ee5ca03281dc8-eFmUsCjsjpXRfjbW
SMTP_FROM_EMAIL=dubbalwaryash@gmail.com
EMAIL_FROM=dubbalwaryash@gmail.com
```

**Email Configuration:**
- Development and production now support Brevo SMTP
- Falls back to console backend if SMTP credentials not set (dev only)
- Production supports both Brevo and SendGrid (via env vars)

## 2. Email Template System ✅

### Base Template
- **Location:** `trip_planner/templates/trip_planner/emails/base.html`
- Features:
  - Spotter AI branded header (green gradient)
  - Responsive design (mobile-friendly)
  - Outlook-compatible
  - Reusable footer with support/privacy/terms links
  - Block structure for easy extension

### Email Templates Created

#### `invitation.html`
- Invitation email with "Accept Invitation" button
- Shows expiry time, inviter name, organization name
- Important information list

#### `welcome.html`
- Welcome new users after account creation
- Shows account details (email, role, org)
- "Go to Dashboard" button

#### `trip_assigned.html`
- Notifies drivers of new trip assignments
- Trip details box with current/pickup/dropoff locations
- Distance, duration, vehicle info
- "View Full Trip Details" button

#### `violation_alert.html`
- HOS violation notifications
- Color-coded by severity (CRITICAL/ERROR/WARNING)
- Violation details and action required
- Link to view trip and violations

### Email Service Functions
**Location:** `trip_planner/services/email_service.py`

Functions:
- `send_invitation_email()` - Invitation emails
- `send_welcome_email()` - Welcome new users
- `send_trip_assigned_email()` - Trip assignment notifications
- `send_violation_alert_email()` - HOS violation alerts

## 3. User Model Renamed ✅

**Changed:** `CustomUser` → `User` throughout the codebase

**Updated files:**
- `trip_planner/models/user.py` - Model definition
- `trip_planner/models/__init__.py` - Exports
- `eld_backend/settings/base.py` - AUTH_USER_MODEL, Jazzmin config
- `trip_planner/admin.py` - Admin registration
- `trip_planner/views/trip_views.py` - Import and usage
- `trip_planner/services/invitation_service.py` - References
- `trip_planner/management/commands/seed_dev_data.py` - Seed data
- `trip_planner/serializers/auth.py` - Authentication serializers

**Why:** More Pythonic and clearer naming convention

## 4. Serializer Enhancements ✅

### OrganizationMember (MemberSerializer)
**Added fields:**
- `email_verified` - User's email verification status
- `deactivated_by_email` - Who deactivated the member
- `invited_by_email` - Who invited the member

### Trip (TripListSerializer & TripDetailSerializer)
**Added fields:**
- `vehicle_number` - Assigned vehicle truck number
- `remaining_cycle_hours` - Remaining HOS cycle hours
- `updated_at` - Last update timestamp (list view)

### All Serializers Review
- ✅ All model attributes now exposed in appropriate serializers
- ✅ Method fields use `@extend_schema_field` for proper OpenAPI docs
- ✅ Read-only fields properly marked
- ✅ Foreign key relationships exposed with human-readable fields

## 5. API Enhancements ✅

### Trip Assignment Email
**Location:** `trip_planner/views/trip_views.py` - `TripAssignView`

When a trip is assigned to a driver:
1. Trip status updated to `ASSIGNED`
2. **Email automatically sent** to driver with:
   - Trip details (pickup/dropoff/distance/duration)
   - Vehicle information
   - Planned start time
   - Link to view full trip

### Queryset Optimizations
- **TripListView:** Now uses `select_related("vehicle")` to prevent N+1 queries
- All list views properly preload relationships

## 6. JWT Payload ✅

Access token now includes:
- `user_id` - User UUID
- `email` - User email address
- `org_id` - Active organization UUID
- `role` - Member role (ORG_ADMIN, DRIVER, etc.)
- `member_id` - OrganizationMember UUID
- `driver_profile_id` - DriverProfile UUID (if exists)

## 7. Pagination System ✅

### Custom Pagination Class
**Location:** `trip_planner/pagination.py`

**Response Format:**
```json
{
  "results": [...],
  "pagination": {
    "count": 100,
    "page": 1,
    "page_size": 25,
    "next": "http://...",
    "previous": null,
    "has_next": true,
    "has_prev": false
  }
}
```

### List Endpoints with Pagination
All support:
- `page` - Page number (1-based)
- `page_size` - Items per page (max 100)
- `search` - Endpoint-specific search
- `ordering` - Sort order
- **Trips:** Filter by `status`
- **Invitations:** Filter by `status`
- **Vehicles:** Search truck_number, license_plate, vin
- **Members:** Search email, first_name, last_name

## 8. Swagger/ReDoc Documentation ✅

### Fixed Authentication Warnings
- `CookieJWTAuthExtension` now properly registered in `trip_planner/apps.py`
- Swagger shows both BearerAuth and CookieAuth
- No more "could not resolve authenticator" warnings

### Documented Query Parameters
All list endpoints now show:
- Pagination parameters (page, page_size)
- Search fields
- Filter fields (status, etc.)
- Ordering options

### Response Schemas
- Custom `paginated_list_schema()` helper shows proper response structure
- All enum values properly documented
- Method fields have type hints via `@extend_schema_field`

## Environment Setup

### Virtual Environment
**Location:** `spotter-api/venv/`

**Activation:**
```bash
source venv/bin/activate  # Linux/macOS
# or
venv\Scripts\activate     # Windows
```

**Old folders removed:**
- ✅ `/home/hc-user/Videos/eld_venv` - deleted
- ✅ `/home/hc-user/Videos/eld_backend` - deleted

## Testing Checklist

### Email Testing
1. **Invitation:**
   - POST `/api/v1/invitations/` with valid email/role
   - Check email delivery via Brevo
   - Verify template rendering

2. **Welcome:**
   - Accept an invitation
   - Check welcome email sent

3. **Trip Assignment:**
   - POST `/api/v1/trips/{id}/assign/` with driver_id
   - Verify driver receives email with trip details

### API Testing
1. **Pagination:**
   - GET `/api/v1/trips/?page=1&page_size=10`
   - Verify `pagination` object in response
   - Check `has_next` and `has_prev` fields

2. **Search/Filter:**
   - GET `/api/v1/trips/?search=chicago&status=DRAFT`
   - GET `/api/v1/vehicles/?search=ABC-123`
   - GET `/api/v1/members/?search=john`

3. **New Fields:**
   - GET `/api/v1/org/members/` - verify `email_verified`, `deactivated_by_email`
   - GET `/api/v1/trips/` - verify `vehicle_number`, `remaining_cycle_hours`

### Swagger Testing
1. Open `/api/docs/`
2. Verify no authentication warnings
3. Check list endpoints show pagination/search/filter params
4. Verify response schemas show `results` + `pagination`

## Database Migration Required

**Note:** The User model rename (`CustomUser` → `User`) requires a migration if existing migrations reference `CustomUser`.

**If you have existing data:**
```bash
# Django tracks the model name but table name stays "users"
# No data migration needed - just code changes
python manage.py makemigrations
python manage.py migrate
```

**Fresh setup:**
```bash
python manage.py migrate
python manage.py seed_dev_data  # Creates 25 users, 2 orgs, etc.
```

## Quick Start

```bash
# 1. Activate venv
source venv/bin/activate

# 2. Install dependencies (if needed)
pip install -r requirements.txt

# 3. Run migrations
python manage.py migrate

# 4. Create superuser (optional)
python manage.py createsuperuser

# 5. Seed development data (optional)
python manage.py seed_dev_data

# 6. Run server
python manage.py runserver
```

**Access:**
- API Docs: http://localhost:8000/api/docs/
- ReDoc: http://localhost:8000/api/redoc/
- Admin: http://localhost:8000/admin/

## What's Next

Potential enhancements:
- Password reset email template
- Account verification email template
- Trip completion notification
- Daily HOS summary email
- Weekly/monthly report emails
