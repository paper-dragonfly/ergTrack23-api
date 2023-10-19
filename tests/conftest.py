import sys
# do what it takes to get the test imports working
sys.path.append(".")

import pytest
from fastapi.testclient import TestClient
from src.main import app


API_SERVER = "http://api:8080"


@pytest.fixture(scope="module")
def client() -> TestClient:
    return TestClient(app)
