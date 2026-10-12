import os
from pathlib import Path

os.environ["DATABASE_URL"] = "sqlite:///./test_ai_document_search.db"
os.environ["SECRET_KEY"] = "test-secret-key-that-is-long-enough-for-tests"
os.environ["UPLOAD_DIR"] = "test_uploads"
os.environ["RATE_LIMIT_PER_MINUTE"] = "1000"
os.environ["QDRANT_URL"] = ""

import pytest
from fastapi.testclient import TestClient
from app.api.main import app
from app.db.session import Base, engine

@pytest.fixture(autouse=True)
def clean_database():
    Base.metadata.drop_all(engine); Base.metadata.create_all(engine); yield; Base.metadata.drop_all(engine); engine.dispose()
    Path("test_ai_document_search.db").unlink(missing_ok=True)

@pytest.fixture
def client():
    with TestClient(app) as test_client: yield test_client

def auth(client, email="reader@example.com"):
    response=client.post("/api/auth/register",json={"email":email,"display_name":"Test Reader","password":"correct-horse-battery"})
    return {"Authorization":f"Bearer {response.json()['access_token']}"}

