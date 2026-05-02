from src.db.main import get_session
from unittest.mock import Mock, AsyncMock
from src import app
from src.auth import routes as auth_routes
from src.books import routes as book_routes
import pytest
from fastapi.testclient import TestClient

mock_session = Mock()
mock_user_service = AsyncMock()
mock_user_service.user_exists.return_value = False
mock_user_service.create_user.return_value = {
    "username": "AhmadMajdi",
    "email": "ahmadbara58@gmail.com",
}

mock_book_service = AsyncMock()

auth_routes.user_service = mock_user_service
auth_routes.send_email = Mock()
book_routes.book_service = mock_book_service


def get_mock_session():
    yield mock_session


def mock_role_checker():
    return True


def mock_access_token_bearer():
    return {
        "user": {"email": "ahmadbara58@gmail.com", "user_uid": "test-uid"},
        "jti": "test-jti",
        "refresh": False,
        "exp": 9999999999,
    }


def mock_refresh_token_bearer():
    return {
        "user": {"email": "ahmadbara58@gmail.com", "user_uid": "test-uid"},
        "jti": "test-jti",
        "refresh": True,
        "exp": 9999999999,
    }


app.dependency_overrides[get_session] = get_mock_session
app.dependency_overrides[auth_routes.role_checker] = mock_role_checker
app.dependency_overrides[auth_routes.access_token_bearer] = mock_access_token_bearer
app.dependency_overrides[auth_routes.refresh_token_bearer] = mock_refresh_token_bearer
app.dependency_overrides[book_routes.role_checker] = mock_role_checker
app.dependency_overrides[book_routes.access_token_bearer] = mock_access_token_bearer


@pytest.fixture
def fake_session():
    return mock_session


@pytest.fixture
def fake_user_service():
    return mock_user_service


@pytest.fixture
def fake_book_service():
    return mock_book_service


@pytest.fixture
def test_client():
    return TestClient(app, base_url="http://localhost")


