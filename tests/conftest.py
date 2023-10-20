import sys
# do what it takes to get the test imports working
sys.path.append(".")

import pytest
from fastapi.testclient import TestClient
from src.main import app
from tests import utils as tu

API_SERVER = "http://api:8080"


@pytest.fixture(scope="module")
def client() -> TestClient:
    return TestClient(app)

AUTH_UID = "fake-auth-uid"

@pytest.fixture(scope="module")
def headers() -> dict:
    return {"Authorization": tu.generate_token(AUTH_UID)}

@pytest.fixture(scope="module")
def auth_uid() -> str:
    return AUTH_UID