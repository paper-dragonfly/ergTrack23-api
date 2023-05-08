import json
import pdb
import yaml
from PIL import Image
from io import BytesIO
from typing import Union, Dict, List, Tuple
from cryptography.fernet import Fernet
from hashlib import sha256

from src.ocr import hit_textract_api, process_raw_ocr
from src.database import UserTable, WorkoutLogTable

# Load vals from config
with open("config/config.yaml", "r") as f:
    config_data = yaml.load(f, Loader=yaml.FullLoader)

SECRET_STRING = config_data["SECRET_STRING"]
KEY = config_data["FERNET_KEY"]
# create a Fernet instance using KEY
fernet = Fernet(KEY)


def create_encrypted_token(auth_uid: str) -> str:
    # create personal hash token
    unencrypted_string = SECRET_STRING + "BREAK" + auth_uid
    encrypted_token = fernet.encrypt(unencrypted_string.encode())
    return encrypted_token


def validate_user_token(authorization: str) -> Union[str, bool]:
    # decrypt token
    token = authorization.split(" ")[1]
    decMessage_list = fernet.decrypt(token).decode().split("BREAK")
    print(decMessage_list)
    if decMessage_list[0] == SECRET_STRING:
        return decMessage_list[1]
    return False


def get_user_id(auth_uid: str, session):
    try:
        user = session.query(UserTable).filter_by(auth_uid=auth_uid).first()
        return user.user_id
    except Exception as e:
        print(e)
        return False
