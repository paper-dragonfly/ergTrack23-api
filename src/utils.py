import json
import pdb
import yaml
from PIL import Image
from io import BytesIO
from typing import Union
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


def get_processed_ocr_data(erg_photo) -> dict:
    # convert bytes to byte array & create photo_hash
    byte_array = bytearray(erg_photo.file.read())
    photo_hash = sha256(byte_array).hexdigest()
    # Check if image is already in raw_ocr library
    with open("src/rawocr.json", "r") as f:
        raw_ocr_library = json.load(f)
    if erg_photo.filename in raw_ocr_library.keys():
        # If yes -> grab raw response
        raw_textract_resp = raw_ocr_library[erg_photo.filename]
    # If no -> create byte array, display img, send to textract
    else:
        # open image + send to AWS Textract for OCR extraction
        pil_image = Image.open(BytesIO(byte_array))
        pil_image.show()
        raw_textract_resp = hit_textract_api(byte_array)
        # TODO create sha256 hash for img and save image to cloud storage
        # save raw_resp to raw_ocr library + TODO image hash
        with open("src/rawocr.json", "w") as f:
            raw_ocr_library[erg_photo.filename] = raw_textract_resp
            json.dump(raw_ocr_library, f)
    # TODO return image_hash too
    return process_raw_ocr(raw_textract_resp, photo_hash)


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
