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


class InvalidTokenError(Exception):
    """Raised if userToken does not contain valid Secret String"""

    def __init__(self, message="Unauthorized Request: invalid token"):
        self.message = message
        super().__init__(self.message)


def create_encrypted_token(auth_uid: str) -> str:
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


def custom_processor(logger, log_method, event_json_str: str) -> str:
    event_dict = json.loads(event_json_str)

    event_dict = _add_author_key(event_dict)    
    event_dict = _convert_level_to_severity(event_dict)
    event_dict = _convert_event_to_message(event_dict)
    return json.dumps(event_dict)


def _add_author_key(event_dict: dict) -> dict:
    event_dict['author'] = 'api-code'
    return event_dict


def _convert_level_to_severity(event_dict: dict) -> dict:
    """Mapping from structlog log level to Google Cloud severity"""
    level_to_severity = {
        'debug': 'DEBUG',
        'info': 'INFO',
        'warning': 'WARNING',
        'error': 'ERROR',
        'exception': 'ERROR',
        'critical': 'CRITICAL',
    }
    if 'level' in event_dict:
        event_dict['severity'] = level_to_severity[event_dict['level']]
        del event_dict['level']
    return event_dict


def _convert_event_to_message(event_dict: dict) -> dict:
    """Convert structlog event to message for Google Cloud"""
    if 'event' in event_dict:
        event_dict['message'] = event_dict['event']
        del event_dict['event']
    return event_dict
