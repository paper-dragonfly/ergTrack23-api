import pdb
from http import HTTPStatus
import json
from io import BytesIO
from typing import Optional, List, Union
import time
import yaml
from datetime import datetime

from fastapi import FastAPI, Request, File, UploadFile, Form, Header
from fastapi.middleware.cors import CORSMiddleware
from firebase_admin import credentials, auth
import firebase_admin
from PIL import Image
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.schemas import PostWorkoutSchema, OcrDataReturn, WorkoutLogSchema
from src.classes import Response
from src.utils import (
    create_encrypted_token,
    validate_user_token,
    get_user_id,
)
from src.database import UserTable, WorkoutLogTable
from src.helper import process_outgoing_workouts, upload_blob, get_processed_ocr_data

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

# Load config file values
with open("config/config.yaml", "r") as f:
    config_data = yaml.load(f, Loader=yaml.FullLoader)

SECRET_STRING = config_data["SECRET_STRING"]
FAKE_DB = config_data["FAKE_DB"]
CONC_STR = "postgresql://katcha@localhost:5432/erg_track"

# sqlalchemy setup
engine = create_engine(CONC_STR, echo=True)
Session = sessionmaker(bind=engine)


######  END POINTS ######


@app.get("/health")
def read_health():
    return {"API status": HTTPStatus.OK}


@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.get("/login/")
async def read_login(authorization: str = Header(...)):
    """
    Receives id_token
    Validate user with Firebase, add to ergTrack db if new, generate encrypted token
    Return encrypted token
    """
    id_token = authorization.split(" ")[1]
    print("Auth val: ", authorization)
    try:
        # hack fix added delay - TODO find better  solution
        print(datetime.now())
        time.sleep(1.0)
        print(datetime.now())
        decoded_token = auth.verify_id_token(id_token)
        print("decoded token ", decoded_token)
        # token is valid
        auth_uid = decoded_token["uid"]
        # check if user in db, if not add user
        with Session() as session:
            try:
                existing_user = (
                    session.query(UserTable.auth_uid)
                    .filter_by(auth_uid=auth_uid)
                    .scalar()
                )
                if not existing_user:
                    new_user = UserTable(
                        auth_uid=auth_uid,
                        user_name=decoded_token["name"],
                        email=decoded_token["email"],
                    )
                    session.add(new_user)
                    session.commit()
            except Exception as e:
                message = "cannot validate user or cannot add user to db"
                print(message)
                print(e)
                return Response(status_code=500, error_message=e)
        encrypted_token = create_encrypted_token(auth_uid)
    except auth.InvalidIdTokenError as err:
        print("Error: ", str(err))
        # Token invalid
        return Response(status_code=400, error_message=f"Token invalin: {err}")
    except:
        return Response(
            status_code=400, error_message="no token recieved or other issue"
        )
    return Response(body={"user_token": encrypted_token})


# @app.get("/email/")
# def read_email(authorization: str = Header(...)):
#     user_token = authorization.split(" ")[1]
#     valid_token = validate_user_token(user_token)
#     if not valid_token:
#         return Response(status_code=401, error_message="Invalid userToken")
#     # get data from db
#     email = FAKE_DB["email"][FAKE_DB["user_id"].index(decMessage_list[1])]
#     return Response(body={"user_email": email})


@app.post("/ergImage")
async def create_extract_and_process_ergImage(ergImg: UploadFile = File(...)):
    """
    Receives UploadFile containing photo of erg screen,
    sends image to Textract for OCR, processes raw result
    Returns processed data
    """
    try:
        image_bytes = ergImg.file.read()
        filename = ergImg.filename
        ocr_data: OcrDataReturn = get_processed_ocr_data(filename, image_bytes)
        upload_blob("erg_memory_screen_photos", image_bytes, ocr_data["photo_hash"])
    except Exception as e:
        print("/ergImage exception", e)
        return Response(status_code=400, error_message=str(e))
    return Response(body=ocr_data)


@app.get("/workout")
async def read_workout(authorization: str = Header(...)):
    """Get all workout data for user"""
    auth_uid = validate_user_token(authorization)
    if not auth_uid:
        return Response(status_code=401, error_message="Unauthorized Request")
    with Session() as session:
        try:
            user_id = get_user_id(auth_uid, session)
            workouts = session.query(WorkoutLogTable).filter_by(user_id=user_id).all()
            print("workouts retreived")
            print(workouts)
            workouts_processed: List[WorkoutLogSchema] = process_outgoing_workouts(
                workouts
            )
            print(workouts_processed)
            return Response(body={"workouts": workouts_processed})
        except Exception as e:
            print(e)
            return Response(status_code=500, error_message=e)


@app.post("/workout")
async def create_workout(
    workoutData: PostWorkoutSchema, authorization: str = Header(...)
):
    """
    Receives: workout data and id_token
    Add workout data to ergTrack db
    Retruns: success message
    """
    # pdb.set_trace()
    # confirm data coming from valid user
    auth_uid = validate_user_token(authorization)
    if not auth_uid:
        return Response(status_code=401, error_message="Unauthorized Request")
    print(workoutData)
    with Session() as session:
        try:
            # get user_id
            user_id = get_user_id(auth_uid, session)
            # create data entry (WorkoutLogTable  instance)
            subworkouts_json = json.dumps(workoutData.tableMetrics[1:])
            workout_entry = WorkoutLogTable(
                user_id=user_id,
                description=workoutData.woMetaData["workoutName"],
                date=workoutData.woMetaData["workoutDate"],
                time=workoutData.tableMetrics[0]["time"],
                meter=workoutData.tableMetrics[0]["distance"],
                split=workoutData.tableMetrics[0]["split"],
                stroke_rate=workoutData.tableMetrics[0]["strokeRate"],
                interval=False,
                image_hash=workoutData.photoHash,
                subworkouts=subworkouts_json,
                comment=workoutData.woMetaData["comment"],
            )

            # use sqlAlchemy to add entryy to db

            session.add(workout_entry)
            session.commit()
        except Exception as e:
            return Response(status_code=500, error_message=e)
    return Response(body={"message": "workout posted successfully"})


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
