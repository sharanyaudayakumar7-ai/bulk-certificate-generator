import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker
import os
import shutil
import time

from app.main import app
from app.database import Base, get_db
from app import models

# Use in-memory SQLite for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)

# Override the database used in the background task for tests
# We can just monkeypatch app.database.SessionLocal
@pytest.fixture(autouse=True)
def mock_db_session(monkeypatch):
    import app.database
    monkeypatch.setattr(app.database, "SessionLocal", TestingSessionLocal)
    
    # Also clean up generated certificates directory before/after
    if os.path.exists("generated_certificates"):
        shutil.rmtree("generated_certificates")
    os.makedirs("generated_certificates", exist_ok=True)
    
    yield
    
    if os.path.exists("generated_certificates"):
        shutil.rmtree("generated_certificates")

def test_create_job():
    payload = {
        "event_name": "Python Conference 2026",
        "date": "2026-10-08",
        "recipients": [
            {"name": "Alice Smith", "email": "alice@example.com"},
            {"name": "Bob Jones", "email": "bob@example.com"}
        ]
    }
    response = client.post("/jobs", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["total_recipients"] == 2
    assert data["status"] == "PENDING"
    assert "id" in data
    
    # Background task should have run (TestClient runs them synchronously if configured, but background_tasks run after response. Actually TestClient runs them after returning response but still synchronously if awaited, wait TestClient handles it in the same thread normally. Let's wait a bit just in case, or since TestClient waits for background tasks to finish, it should be done).
    # Wait, FastAPI TestClient actually blocks until background tasks are completed.
    
    job_id = data["id"]
    
    # Check status
    response = client.get(f"/jobs/{job_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "COMPLETED"
    assert data["successful_generations"] == 2
    assert data["failed_generations"] == 0
    
    # Check certificates
    response = client.get(f"/jobs/{job_id}/certificates")
    assert response.status_code == 200
    certs = response.json()
    assert len(certs) == 2
    assert certs[0]["status"] == "SUCCESS"
    
    cert_id = certs[0]["id"]
    
    # Get PDF
    response = client.get(f"/certificates/{cert_id}")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"

def test_invalid_input():
    payload = {
        "event_name": "",
        "date": "2026-10-08",
        "recipients": []
    }
    response = client.post("/jobs", json=payload)
    assert response.status_code == 422
    
    payload = {
        "event_name": "Event",
        "date": "2026-10-08",
        "recipients": [
            {"name": "Invalid Email", "email": "not-an-email"}
        ]
    }
    response = client.post("/jobs", json=payload)
    assert response.status_code == 422

def test_individual_certificate_failure(monkeypatch):
    import app.certificate
    
    original_generate = app.certificate.generate_certificate_pdf
    
    def mock_generate(*args, **kwargs):
        if kwargs.get('recipient_name') == "Fail Me":
            raise Exception("Simulated PDF generation error")
        return original_generate(*args, **kwargs)
        
    monkeypatch.setattr(app.certificate, "generate_certificate_pdf", mock_generate)
    
    payload = {
        "event_name": "Test Event",
        "date": "2026-10-08",
        "recipients": [
            {"name": "Good User", "email": "good@example.com"},
            {"name": "Fail Me", "email": "fail@example.com"}
        ]
    }
    response = client.post("/jobs", json=payload)
    assert response.status_code == 201
    job_id = response.json()["id"]
    
    # Wait for test client
    
    response = client.get(f"/jobs/{job_id}")
    data = response.json()
    assert data["status"] == "COMPLETED_WITH_ERRORS"
    assert data["successful_generations"] == 1
    assert data["failed_generations"] == 1
    
    response = client.get(f"/jobs/{job_id}/certificates")
    certs = response.json()
    assert len(certs) == 2
    
    for cert in certs:
        if cert["recipient_name"] == "Fail Me":
            assert cert["status"] == "FAILED"
            assert cert["error_message"] == "Simulated PDF generation error"
            
            # Trying to get failed PDF should return 400
            pdf_resp = client.get(f"/certificates/{cert['id']}")
            assert pdf_resp.status_code == 400
        else:
            assert cert["status"] == "SUCCESS"
            pdf_resp = client.get(f"/certificates/{cert['id']}")
            assert pdf_resp.status_code == 200
