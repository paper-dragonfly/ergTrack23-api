from tests import utils as tu
from unittest.mock import patch
from src.schemas import PutUserSchema, PatchUserSchema, PostWorkoutSchema, PostTeamDataSchema, PostFeedbackSchema, LoginRequest

USERNAME = "fake-username"
EMAIL = "fake@email.com"

def test_health_succeeds(client):
    resp = client.get("/health")
    assert resp.status_code == 200


def test_get_root_succeeds(client):
    resp = client.get("/")
    assert resp.status_code == 200


def test_read_login_succeeds(client, headers, auth_uid):
    login_request = LoginRequest(email=EMAIL).dict()
    with patch("src.main.create_new_auth_uid", return_value=auth_uid):
        resp = client.post("/login/", headers=headers, json=login_request)
    
    assert resp.json()["status_code"] == 200


def test_read_user_succeeds(client, headers):
    resp = client.get("/user", headers=headers)
    assert resp.json()["status_code"] == 200
    

def test_update_user_succeeds(client, headers):
    put_user = PutUserSchema(user_name=USERNAME, email=EMAIL, sex="M").dict()
    resp = client.put("/user", headers=headers, json=put_user)
    assert resp.json()["status_code"] == 200
    

def test_patch_user_succeeds(client, headers):
    # get the exisnting user info because otherwise you will lose the team data
    resp = client.get("/user", headers=headers)
    patch_user = PatchUserSchema(**resp.json()["body"]).todict()
    resp = client.patch("/user", headers=headers, json=patch_user)
    assert resp.json()["status_code"] == 200


def test_create_extract_and_process_ergImage_succeeds(client, headers):
    with open("./tests/erg-screen.jpeg", "rb") as f:
        files = {"photo1": ("erg-screen.jpeg", f, "image/jpeg")}
        with patch("src.main.upload_blob"):
            resp = client.post("/ergImage", headers=headers, files=files)
    assert "photo_hash" in resp.json()["body"]


def test_create_workout_succeeds(client, headers):
    # TODO gotta generate data for the workout
    post_workout = PostWorkoutSchema(**{"woMetaData":{"workoutName":"1:00:00","workoutDate":"2023-09-16","comment":"","postToTeam":False},"tableMetrics":[{"id":"TE-UOErDDeuwNXFk_QBFM","time":"1:00:00.0","distance":14496,"split":"2:04.1","strokeRate":24,"heartRate":176},{"id":"9Xp9sA9uUHuLCwFyzB6JK","time":"10:00.0","distance":2418,"split":"2:04.0","strokeRate":22,"heartRate":169},{"id":"pHb06GNbEUNEAIvNrmMT4","time":"20:00.0","distance":2480,"split":"2:00.9","strokeRate":26,"heartRate":175},{"id":"VtosZSQmjL7fHuNxQ9Cos","time":"30:00.0","distance":2398,"split":"2:05.1","strokeRate":23,"heartRate":176},{"id":"xdNcyh-7DnNZAl28sql41","time":"40:00.0","distance":2379,"split":"2:06.1","strokeRate":23,"heartRate":176},{"id":"PEDcXxNnicx20HeL_BIz_","time":"50:00.0","distance":2403,"split":"2:04.8","strokeRate":26,"heartRate":176},{"id":"CCGHKayMc7B9eGFVJqqcl","time":"1:00:00.0","distance":2418,"split":"2:04.0","strokeRate":25,"heartRate":184}],"photoHash":["a905f7bc6995444d45b47f8db3009dc2570ae5e8f33ad2f0ccbe4b84562ba52f"]}).dict()
    resp = client.post("/workout", headers=headers, json=post_workout)
    assert resp.json()["status_code"] == 200


def test_read_workout_succeeds(client, headers):
    resp = client.get("/workout", headers=headers)
    assert "workouts" in resp.json()["body"]


def test_delete_workout_succeeds(client, headers):
    resp = client.get("/workout", headers=headers)
    workout_id = resp.json()["body"]["workouts"][0]["workout_id"]
    resp = client.delete(f"/workout/{workout_id}", headers=headers)
    assert resp.json()["status_code"] == 200


def test_write_team_succeeds(client, headers):
    post_team_data = PostTeamDataSchema(teamName="fake-team2", teamCode="fake-code").dict()
    resp = client.post("/team", headers=headers, json=post_team_data)
    assert resp.json()["status_code"] in (200, 403)


def test_read_team_succeeds(client, headers):
    resp = client.get("/team", headers=headers)
    assert "team_member" in resp.json()["body"]


def test_update_team_succeeds(client, headers):
    resp = client.get("/team", headers=headers)
    team_id = resp.json()["body"]["team_info"]["team_id"]
    post_team_data = PostTeamDataSchema(teamName="fake-team3", teamCode="fake-code").dict()
    resp = client.put(f"/team/{team_id}", headers=headers, json=post_team_data)


def test_write_join_team_succeeds(client, headers):
    post_team_data = PostTeamDataSchema(teamName="fake-team3", teamCode="fake-code").dict()
    resp = client.patch(f"/jointeam", headers=headers, json=post_team_data)
    assert resp.json()["status_code"] == 200


def test_read_teamlog_succeeds(client, headers):
    resp = client.get("/teamlog", headers=headers)
    assert "team_workouts" in resp.json()["body"]


def test_read_team_info_succeeds(client, headers):
    resp = client.get("/teamadmin", headers=headers)
    assert "team_info" in resp.json()["body"]


def test_update_admin_succeeds(client, headers):
    resp = client.get("/user", headers=headers)
    new_admin_id = resp.json()["body"]["user_id"]
    resp = client.patch(f"/transferadmin/{new_admin_id}", headers=headers)
    assert resp.json()["status_code"] == 200


def test_create_feedback_succeeds(client, headers):
    post_feedback = PostFeedbackSchema(**{"feedbackCategory": "fake-category", "comment": "fake-comment"}).dict()
    resp = client.post("/feedback", headers=headers, json=post_feedback)
    assert resp.json()["status_code"] == 200
