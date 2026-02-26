#!/usr/bin/env python
"""
Test API endpoints for each role from seed_dev_data.
Run: python scripts/test_api_roles.py
Requires: API running at http://127.0.0.1:8000, seed data loaded.
"""

import json
import sys
import requests

BASE = "http://127.0.0.1:8000/api/v1"


def api_url(path: str) -> str:
    return f"{BASE.rstrip('/')}/{path.lstrip('/')}"
SEED_PASSWORD = "SpotterDev123!"

# One user per role (Swift org). Format: (email, role_label)
USERS = [
    ("superadmin@spotter.ai", "PLATFORM_ADMIN"),
    ("admin@swift.com", "ORG_ADMIN"),
    ("dispatch1@swift.com", "DISPATCHER"),
    ("fleet1@swift.com", "FLEET_MANAGER"),
    ("driver1@swift.com", "DRIVER"),
    ("fleet2@swift.com", "FLEET_MANAGER"),
]

ENDPOINTS = [
    ("GET", "/auth/me/", "auth-me"),
    ("GET", "/org/", "org-detail"),
    ("GET", "/org/members/", "org-members"),
    ("GET", "/invitations/", "invitations"),
    ("GET", "/vehicles/", "vehicles"),
    ("GET", "/trips/", "trips"),
    ("POST", "/trips/plan/", "trips-plan", {"current_location": "Chicago, IL", "pickup_location": "Dallas, TX", "dropoff_location": "Atlanta, GA", "cycle_used_hours": 10}),
]


def login(email: str) -> str | None:
    r = requests.post(
        api_url("auth/login/"),
        json={"email": email, "password": SEED_PASSWORD},
        timeout=10,
    )
    if r.status_code != 200:
        return None
    data = r.json()
    return data.get("access_token") or data.get("access")


def run_tests():
    results = []
    for email, role in USERS:
        token = login(email)
        if not token:
            results.append((role, email, "LOGIN FAILED", []))
            continue

        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        role_results = []

        for item in ENDPOINTS:
            if len(item) == 4:
                method, path, name, body = item
            else:
                method, path, name = item
                body = None

            url = api_url(path)
            try:
                if method == "GET":
                    r = requests.get(url, headers=headers, timeout=10)
                else:
                    r = requests.post(url, headers=headers, json=body or {}, timeout=15)
                status = r.status_code
                if status in (200, 201, 204):
                    role_results.append((name, "OK", status))
                else:
                    detail = ""
                    try:
                        d = r.json()
                        detail = d.get("detail", str(d))[:80]
                    except Exception:
                        detail = r.text[:80] if r.text else ""
                    role_results.append((name, f"{status} {detail}", status))
            except Exception as e:
                role_results.append((name, f"ERR: {e}", 0))

        results.append((role, email, "OK", role_results))

    return results


def main():
    print("Testing API for each role...\n")
    results = run_tests()

    for role, email, login_status, endpoints in results:
        print(f"=== {role} ({email}) ===")
        if login_status != "OK":
            print(f"  Login: FAILED\n")
            continue
        print("  Login: OK")
        for name, msg, code in endpoints:
            icon = "✓" if code in (200, 201, 204) else "✗"
            print(f"  {icon} {name}: {msg}")
        print()

    # Summary
    failed = sum(1 for r in results if r[2] != "OK" or any(e[2] not in (200, 201, 204) for e in r[3]))
    if failed:
        print(f"Summary: {failed} role(s) had failures")
        sys.exit(1)
    print("Summary: All roles passed")
    sys.exit(0)


if __name__ == "__main__":
    main()
