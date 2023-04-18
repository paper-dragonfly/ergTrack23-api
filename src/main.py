import pdb
from http import HTTPStatus
import json
from io import BytesIO
from PIL import Image
from typing import Optional
import time
import yaml

from fastapi import FastAPI, Request, File, UploadFile, Form, Header
from fastapi.middleware.cors import CORSMiddleware
from firebase_admin import credentials, auth
import firebase_admin
from cryptography.fernet import Fernet

from src.schemas import PostWorkoutSchema, OcrDataReturn
from src.classes import Response
from src.ocr import hit_textract_api, process_raw_ocr
from src.utils import get_processed_ocr_data

app = FastAPI()

origins = ["http://localhost:3000"]
# Add CORS middleware to the app
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# initialize Firebase Admin SDK
# Note: can also store credentials as environment variable: export GOOGLE_APPLICATION_CREDENTIALS =  'path/to/sercice-account-key.json'
cred = credentials.Certificate("config/ergtracker-firebase-adminsdk.json")
firebase_admin.initialize_app(cred)

# Load vals from config
with open("config/config.yaml", "r") as f:
    config_data = yaml.load(f, Loader=yaml.FullLoader)

SECRET_STRING = config_data["SECRET_STRING"]
FAKE_DB = config_data["FAKE_DB"]

# generate key for encrypting and decrypting
KEY = Fernet.generate_key()
# create a Fernet instance using KEY
fernet = Fernet(KEY)


@app.get("/health")
def read_health():
    return {"API status": HTTPStatus.OK}


@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.get("/login/")
async def read_login(authorization: str = Header(...)):
    # pdb.set_trace()
    id_token = authorization.split(" ")[1]
    print("Auth val: ", authorization)
    try:
        # hack fix added delay - TODO find better  solution
        time.sleep(0.1)
        decoded_token = auth.verify_id_token(id_token)
        print("decoded token ", decoded_token)
        # token is valid
        user_id = decoded_token["uid"]
        # check if user in db
        if not user_id in FAKE_DB["user_id"]:
            # name = decoded_token["name"]
            # email = decoded_token["email"]
            # user_id = decoded_token['uid']
            FAKE_DB["name"].append(decoded_token["name"])
            FAKE_DB["email"].append(decoded_token["email"])
            FAKE_DB["user_id"].append(user_id)
        # create personal hash token
        unencrypted_string = SECRET_STRING + "BREAK" + user_id
        encrypted_token = fernet.encrypt(unencrypted_string.encode())
    except auth.InvalidIdTokenError as err:
        print("Error: ", str(err))
        # Token invalid
        return Response(status_code=400, error_message=f"Token invalin: {err}")
    except:
        return Response(
            status_code=400, error_message="no token recieved or other issue"
        )
    return Response(body={"user_token": encrypted_token})


@app.get("/email/")
def read_email(authorization: str = Header(...)):
    user_token = authorization.split(" ")[1]
    # decrypt token
    decMessage_list = fernet.decrypt(user_token).decode().split("BREAK")
    print(decMessage_list)
    if decMessage_list[0] != SECRET_STRING:
        return Response(status_code=401, error_message="Invalid userToken")
    else:
        email = FAKE_DB["email"][FAKE_DB["user_id"].index(decMessage_list[1])]
        return Response(body={"user_email": email})


@app.post("/ergImage")
async def create_extract_and_process_ergImage(ergImg: UploadFile = File(...)):
    ocr_data: OcrDataReturn = get_processed_ocr_data(ergImg)
    # TODO: if successful -> use cabinet to save Image to cloudStorage
    # TODO: will need to add image_hash to response

    return Response(body=ocr_data)


@app.post("/workout")
async def create_workout(workoutData: PostWorkoutSchema):
    print(workoutData)
    return Response(body={"message": "success  post to workout"})


@app.post("/sandbox")
async def create_sandbox(
    name: str = Form(...), age: str = Form(...), image: UploadFile = File(...)
):
    form_data = {"name": name, "age": age}
    print(form_data)
    byte_array = bytearray(image.file.read())
    pil_image = Image.open(BytesIO(byte_array))
    pil_image.show()
    return Response(body={"message": "success", "formdata": form_data})
