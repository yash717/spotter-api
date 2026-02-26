# Admin Panel URLs - Spotter AI

## ⚠️ Important: Model Name Changed

**Old URL (doesn't work):** `http://localhost:8000/admin/trip_planner/customuser/`

**New URL (correct):** `http://localhost:8000/admin/trip_planner/user/`

The model was renamed from `CustomUser` to `User`, so all admin URLs now use `/user/` instead of `/customuser/`.

---

## Admin Panel URLs

### Main Admin
- **Admin Home:** http://localhost:8000/admin/

### Authentication & Authorization
- **Users:** http://localhost:8000/admin/trip_planner/user/
- **Groups:** http://localhost:8000/admin/auth/group/

### Organizations
- **Organizations:** http://localhost:8000/admin/trip_planner/organization/
- **Organization Members:** http://localhost:8000/admin/trip_planner/organizationmember/
- **Invitations:** http://localhost:8000/admin/trip_planner/invitation/

### Fleet Management
- **Driver Profiles:** http://localhost:8000/admin/trip_planner/driverprofile/
- **Vehicles:** http://localhost:8000/admin/trip_planner/vehicle/

### Trip Planning
- **Trips:** http://localhost:8000/admin/trip_planner/trip/
- **Stops:** http://localhost:8000/admin/trip_planner/stop/
- **Daily Log Sheets:** http://localhost:8000/admin/trip_planner/dailylogsheet/
- **Duty Status Segments:** http://localhost:8000/admin/trip_planner/dutystatussegment/
- **HOS Violations:** http://localhost:8000/admin/trip_planner/hosviolation/

### System
- **Geocode Cache:** http://localhost:8000/admin/trip_planner/geocodecache/
- **Audit Logs:** http://localhost:8000/admin/trip_planner/auditlog/

---

## Login Credentials

**Superadmin:**
- URL: http://localhost:8000/admin/
- Email: `superadmin@spotter.ai`
- Password: `SpotterDev123!`

---

## Quick Links

### Most Common Admin Tasks

1. **View All Users:** http://localhost:8000/admin/trip_planner/user/
2. **Add New User:** http://localhost:8000/admin/trip_planner/user/add/
3. **View Organizations:** http://localhost:8000/admin/trip_planner/organization/
4. **View Trips:** http://localhost:8000/admin/trip_planner/trip/
5. **View Vehicles:** http://localhost:8000/admin/trip_planner/vehicle/
6. **View Invitations:** http://localhost:8000/admin/trip_planner/invitation/

---

## Jazzmin Features

The admin panel uses **Jazzmin** theme with:
- Modern, responsive design
- Dark/light mode toggle
- Quick search across models
- Customized icons for each model
- Enhanced navigation

### Search Models
From the admin home, you can search:
- Users (by email, first_name, last_name)
- Organizations (by name, DOT number)

---

## Model URL Pattern

All admin URLs follow this pattern:
```
http://localhost:8000/admin/{app_label}/{model_name}/
```

Where:
- `{app_label}` = `trip_planner` or `auth`
- `{model_name}` = lowercase model name (e.g., `user`, `organization`, `trip`)

**Examples:**
- User model → `/admin/trip_planner/user/`
- Trip model → `/admin/trip_planner/trip/`
- Organization model → `/admin/trip_planner/organization/`

---

## 🔗 Correct Bookmarks

Save these URLs:

**Development:**
- Admin: http://localhost:8000/admin/
- Users: http://localhost:8000/admin/trip_planner/user/
- API Docs: http://localhost:8000/api/docs/
- ReDoc: http://localhost:8000/api/redoc/

**Update any bookmarks** that use `/customuser/` to `/user/`
