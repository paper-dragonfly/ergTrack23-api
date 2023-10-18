from tests.conftest import API_SERVER
from tests import utils as tu
import requests


def test_health():
    resp = requests.get(API_SERVER + "/health")
    assert resp.status_code == 200


def test_get_root():
    resp = requests.get(API_SERVER + "/")
    assert resp.status_code == 200


def test_read_login():
    headers = {"Authorization": tu.generate_token()}
    resp = requests.get(API_SERVER + "/login/", headers=headers)
    assert resp.status_code == 200

