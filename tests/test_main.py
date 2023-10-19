from tests import utils as tu
from unittest.mock import patch
from src.schemas import PutUserSchema, PatchUserSchema, PostWorkoutSchema

USERNAME = "fake-username"
EMAIL = "fake@email.com"
AUTH_UID = "fake-auth-uid"

def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200


def test_get_root(client):
    resp = client.get("/")
    assert resp.status_code == 200


def test_read_login(client):
    headers = {"Authorization": tu.generate_token(AUTH_UID)}
    # resp = requests.get(API_SERVER + "/login/", headers=headers)
    with patch("src.main.auth.verify_id_token", 
               return_value={"uid": AUTH_UID, "name": USERNAME, "email": EMAIL}):
        resp = client.get("/login/", headers=headers)
    
    assert resp.json()["status_code"] == 200


def test_read_user(client):
    headers = {"Authorization": tu.generate_token(AUTH_UID)}
    resp = client.get("/user", headers=headers)
    assert resp.json()["status_code"] == 200
    

def test_update_user(client):
    headers = {"Authorization": tu.generate_token(AUTH_UID)}
    put_user = PutUserSchema(user_name=USERNAME, email=EMAIL, sex="M").dict()
    resp = client.put("/user", headers=headers, json=put_user)
    assert resp.json()["status_code"] == 200
    

def test_patch_user(client):
    headers = {"Authorization": tu.generate_token(AUTH_UID)}
    patch_user = PatchUserSchema(user_name=USERNAME, email=EMAIL).todict()
    resp = client.patch("/user", headers=headers, json=patch_user)
    assert resp.json()["status_code"] == 200
    
def test_create_extract_and_process_ergImage(client):
    pass

def test_create_workout(client):
    # TODO gotta generate data for the workout
    headers = {"Authorization": tu.generate_token(AUTH_UID)}
    post_workout = PostWorkoutSchema(woMetaData={}, tableMetrics=[], photoHash=[]).dict()
    resp = client.post("/workout", headers=headers, json=post_workout)
    assert resp.json()["status_code"] == 200


def test_read_workout(client):
    pass