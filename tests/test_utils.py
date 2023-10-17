from src import utils

def test_token_creation_and_validation():
    token = utils.create_encrypted_token("fake-auth-uid")
    auth_uid = utils.validate_user_token(token)
    print(auth_uid)