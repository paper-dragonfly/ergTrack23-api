from src import utils
from tests import utils as tu

def test_token_creation_and_validation():
    original_uid = "fake-auth-uid"
    final_uid = utils.validate_user_token(tu.generate_token(original_uid))
    assert final_uid == original_uid
