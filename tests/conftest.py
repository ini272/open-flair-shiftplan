# Add this import at the top with the other imports
from datetime import datetime, timedelta
import uuid
import os
import sys
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Add the project root directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Create a mock for the tracer before importing app
mock_tracer = MagicMock()
mock_span = MagicMock()
mock_tracer.start_as_current_span.return_value.__enter__.return_value = mock_span

# Apply the patch
tracer_patch = patch('opentelemetry.trace.get_tracer', return_value=mock_tracer)
tracer_patch.start()

# Now import the app
from app.main import app
from app.database import Base, get_db
from app.models.token import AccessToken

# Create in-memory SQLite database for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="function")
def db():
    """Create a fresh database for each test."""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)

@pytest.fixture(scope="function")
def client(db):
    """Create a test client with a database session."""
    def override_get_db():
        try:
            yield db
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()

# Stop the patch when tests are done
def pytest_sessionfinish(session, exitstatus):
    tracer_patch.stop()

# Add these fixtures at the end of the file
@pytest.fixture(scope="function")
def test_token(db):
    """Create a test token for authentication."""
    token_value = str(uuid.uuid4())
    token = AccessToken(
        name="Test Token",
        token=token_value,
        created_at=datetime.utcnow(),
        expires_at=datetime.utcnow() + timedelta(days=1),
        is_active=True
    )
    db.add(token)
    db.commit()
    db.refresh(token)
    return token_value

@pytest.fixture(scope="function")
def authenticated_client(client, test_token):
    """Create a client that's already authenticated."""
    client.cookies.set("access_token", test_token)
    return client

@pytest.fixture(scope="function")
def test_user(authenticated_client):
    """Create a test user."""
    response = authenticated_client.post(
        "/users/",
        json={"email": "testuser@example.com", "username": "testuser"}
    )
    return response.json()

@pytest.fixture(scope="function")
def test_group(authenticated_client):
    """Create a test group."""
    response = authenticated_client.post(
        "/groups/",
        json={"name": "Test Group"}
    )
    return response.json()

@pytest.fixture(scope="function")
def test_shift(authenticated_client):
    """Create a test shift."""
    start_time = datetime.utcnow() + timedelta(hours=1)
    end_time = start_time + timedelta(hours=2)
    
    response = authenticated_client.post(
        "/shifts/",
        json={
            "title": "Test Shift",
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "capacity": 5
        }
    )
    return response.json()

@pytest.fixture(scope="function")
def user_in_group(authenticated_client, test_user, test_group):
    """Create a user and add them to a group."""
    authenticated_client.post(f"/groups/{test_group['id']}/users/{test_user['id']}")
    return test_user

@pytest.fixture(scope="function")
def user_opted_out(authenticated_client, test_user, test_shift):
    """Create a user who is opted out of a shift."""
    authenticated_client.post(
        "/shifts/user-opt-out",
        json={
            "user_id": test_user["id"],
            "shift_id": test_shift["id"]
        }
    )
    return test_user

@pytest.fixture(scope="function")
def group_opted_out(authenticated_client, test_group, test_shift):
    """Create a group that is opted out of a shift."""
    authenticated_client.post(
        "/shifts/group-opt-out",
        json={
            "group_id": test_group["id"],
            "shift_id": test_shift["id"]
        }
    )
    return test_group