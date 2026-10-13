"""Automated API test suite for ChangeRadar FastAPI backend."""

import sys
from pathlib import Path

# Add backend directory to sys.path so app can be imported directly
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from fastapi.testclient import TestClient
from app.main import app
from app.database import init_db

client = TestClient(app)


def setup_module():
    """Ensure database tables are initialized before tests run."""
    init_db()


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["database"] == "connected"


def test_website_crud_workflow():
    # 1. List websites (GET /websites)
    res_list = client.get("/websites")
    assert res_list.status_code == 200

    # 2. Create website (POST /websites)
    new_website = {
        "name": "NPTEL Swayam Assignment Portal",
        "url": "https://swayam.gov.in/nc_details/NPTEL",
        "category": "Academics",
        "selector": "#timeline-announcements",
        "check_interval_minutes": 60,
    }
    res_create = client.post("/websites", json=new_website)
    assert res_create.status_code == 201
    created_data = res_create.json()
    site_id = created_data["id"]
    assert created_data["name"] == new_website["name"]
    assert created_data["url"] == new_website["url"]
    assert created_data["status"] == "active"

    # 3. Prevent duplicate URL (POST /websites with same URL)
    res_duplicate = client.post("/websites", json=new_website)
    assert res_duplicate.status_code == 409

    # 4. Get by ID (GET /websites/{id})
    res_get = client.get(f"/websites/{site_id}")
    assert res_get.status_code == 200
    assert res_get.json()["id"] == site_id

    # 5. Non-existent ID (GET /websites/999999)
    res_not_found = client.get("/websites/999999")
    assert res_not_found.status_code == 404

    # 6. Delete website (DELETE /websites/{id})
    res_delete = client.delete(f"/websites/{site_id}")
    assert res_delete.status_code == 200

    # 7. Confirm deletion (GET /websites/{id} -> 404)
    res_confirm = client.get(f"/websites/{site_id}")
    assert res_confirm.status_code == 404


def test_website_validation_error():
    bad_payload = {
        "name": "   ",
        "url": "not-a-valid-url"
    }
    res = client.post("/websites", json=bad_payload)
    assert res.status_code == 422
