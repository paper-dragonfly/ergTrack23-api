import os
import json
import pdb
import yaml
from PIL import Image
from io import BytesIO
from typing import Union, Dict, List, Tuple, ByteString
from cryptography.fernet import Fernet
from hashlib import sha256

from src.database import UserTable, WorkoutLogTable


with open("./config/config.yaml", "r") as f:
    config_data = yaml.load(f, Loader=yaml.FullLoader)

# set db connection string based on run environment
DEV_ENV = os.getenv("DEV_ENV")
CONN_STR = config_data["db_conn_str"][DEV_ENV]

SECRET_STRING = config_data["SECRET_STRING"]
KEY = config_data["FERNET_KEY"]
# create a Fernet instance using KEY
fernet = Fernet(KEY)


class InvalidTokenError(Exception):
    """Raised if userToken does not contain valid Secret String"""

    def __init__(self, message="Unauthorized Request: invalid token"):
        self.message = message
        super().__init__(self.message)


def create_encrypted_token(auth_uid: str) -> ByteString:
    # create personal hash token
    unencrypted_string = SECRET_STRING + "BREAK" + auth_uid
    encrypted_token = fernet.encrypt(unencrypted_string.encode())
    return encrypted_token


def validate_user_token(authorization: str) -> Union[str, bool]:
    # decrypt token
    token = authorization.split(" ")[1]
    decMessage_list = fernet.decrypt(token).decode().split("BREAK")
    # print(decMessage_list)
    if decMessage_list[0] == SECRET_STRING:
        return decMessage_list[1]
    raise InvalidTokenError()


def get_user_id(auth_uid: str, session) -> int:
    user = session.query(UserTable).filter_by(auth_uid=auth_uid).first()
    return user.user_id


