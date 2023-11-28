import sys
import os 
# hack to make imports from `src` work
sys.path.append(".")

import pytest
from fastapi.testclient import TestClient

from src.main import app
from tests import utils as tu

AUTH_UID = "fake-auth-uid"

@pytest.fixture(scope="module")
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture(scope="module")
def headers() -> dict:
    return {"Authorization": tu.generate_token(AUTH_UID)}


@pytest.fixture(scope="module")
def auth_uid() -> str:
    return AUTH_UID


@pytest.fixture(scope="module", autouse=True)
def setup():
    """
    This fixture runs before every test module execution.
    To run before every test function, change the scope to `function`.
    """
    if os.environ.get('DEV_ENV') == 'docker_compose':
        tu.reset_postgres()
    else:
        raise Exception('DEV_ENV != docker_compose')