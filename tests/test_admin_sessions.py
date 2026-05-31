import os
import requests
import pytest

API_BASE = os.environ.get("API_BASE", "http://localhost:8000")
ADMIN_TOKEN = os.environ.get("ADMIN_TOKEN")

headers = {"Authorization": f"Bearer {ADMIN_TOKEN}"} if ADMIN_TOKEN else {}


@pytest.mark.skipif(ADMIN_TOKEN is None, reason="Set ADMIN_TOKEN env to run admin tests")
def test_revoke_and_delete_session():
    # Get current sessions
    r = requests.get(f"{API_BASE}/api/admin/sessions", headers=headers, timeout=10)
    assert r.ok
    data = r.json()
    items = data.get("items", [])
    if not items:
        pytest.skip("No sessions available to test")

    # pick the first session
    jti = items[0].get("jti")
    assert jti

    # Revoke
    r = requests.post(f"{API_BASE}/api/admin/sessions/{jti}/revoke", headers=headers, timeout=10)
    assert r.ok

    # Verify session is inactive or removed
    r2 = requests.get(f"{API_BASE}/api/admin/sessions", headers=headers, timeout=10)
    assert r2.ok
    items2 = r2.json().get("items", [])
    # Either session absent or present but is_active == False
    matches = [s for s in items2 if s.get("jti") == jti]
    if matches:
        assert matches[0].get("is_active") in (False, 0)

    # Attempt delete (idempotent)
    r3 = requests.delete(f"{API_BASE}/api/admin/sessions/{jti}", headers=headers, timeout=10)
    assert r3.ok

    # Final check: ensure it's gone
    r4 = requests.get(f"{API_BASE}/api/admin/sessions", headers=headers, timeout=10)
    assert r4.ok
    items4 = r4.json().get("items", [])
    assert not any(s.get("jti") == jti for s in items4)
