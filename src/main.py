import pdb
from http import HTTPStatus
import json
from io import BytesIO
from typing import Optional, List, Union
import time
import yaml
from datetime import datetime
import os

from fastapi import FastAPI, Request, File, UploadFile, Form, Header
from fastapi.middleware.cors import CORSMiddleware
from firebase_admin import credentials, auth
import firebase_admin
from PIL import Image
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.schemas import (
    PostWorkoutSchema,
    OcrDataReturn,
    WorkoutLogSchema,
    Response,
    PutUserSchema,
    PatchUserSchema,
    PostTeamDataSchema
)
from src.utils import (
    create_encrypted_token,
    validate_user_token,
    get_user_id,
)
from src.database import UserTable, WorkoutLogTable, TeamTable
from src.helper import (
    convert_class_instances_to_dicts, 
    upload_blob, 
    get_processed_ocr_data, 
    calculate_watts, 
    calculate_cals,
    calculate_split_var,
    add_user_info_to_workout)

app = FastAPI()

origins = ["http://localhost:3000", "https://ergtrack.com"]
# Add CORS middleware to the app
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load config file values
with open("config/config.yaml", "r") as f:
    config_data = yaml.load(f, Loader=yaml.FullLoader)

# set db connection string based on run environment
DEV_ENV = os.getenv("DEV_ENV")
CONN_STR = config_data["db_conn_str"][DEV_ENV]
SECRET_STRING = config_data["SECRET_STRING"]
# GCLOUD_SA_KEY = config_data['GCLOUD_SA_KEY']
os.environ['AWS_ACCESS_KEY_ID'] = config_data['AWS_ACCESS_KEY_ID']
os.environ['AWS_SECRET_ACCESS_KEY'] = config_data['AWS_SECRET_ACCESS_KEY']

# initialize Firebase Admin SDK
# Note: can either store credentials as environment variable: export GOOGLE_APPLICATION_CREDENTIALS =  'path/to/sercice-account-key.json' OR use path-str
# cred = credentials.Certificate(os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"))
# cred = credentials.Certificate(GCLOUD_SA_KEY) # I don't think this is right, points to file name not path. 
# when no 'cred' given, searches for default
firebase_admin.initialize_app()


# sqlalchemy setup
engine = create_engine(CONN_STR, echo=True)
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
        time.sleep(2.0)
        print(datetime.now())
        decoded_token = auth.verify_id_token(id_token)
        print("decoded token ", decoded_token)
        # token is valid
        auth_uid = decoded_token["uid"]
        # check if user in db, if not add user
        with Session() as session:
            try:
                existing_user = (
                    session.query(UserTable)
                    .filter_by(auth_uid=auth_uid)
                    .one_or_none()
                )
                team_id = existing_user.team
                if not existing_user:
                    new_user = UserTable(
                        auth_uid=auth_uid,
                        user_name=decoded_token["name"],
                        email=decoded_token["email"],
                    )
                    session.add(new_user)
                    session.commit()
                    team_id = None
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
    return Response(body={"user_token": encrypted_token, "team_id": team_id})


@app.get("/user")
async def read_user(authorization: str = Header(...)):
    """
    Recieves user_id
    Returns all data from UserTable for that user
    """
    # confirm data coming from valid user
    auth_uid = validate_user_token(authorization)
    if not auth_uid:
        return Response(status_code=401, error_message="Unauthorized Request")
    try:
        with Session() as session:
            user_id = get_user_id(auth_uid, session)
            user_info = session.query(UserTable).get(user_id).__dict__
            return Response(body=user_info)
    except Exception as e:
        print(e)
        return Response(status_code=500, error_message=e)


@app.put("/user")
async def update_user(new_user_info: PutUserSchema, authorization: str = Header(...)):
    """
    Recieves updated user data
    Updates database
    Returns success message
    """
    # confirm data coming from valid user
    print(new_user_info)
    auth_uid = validate_user_token(authorization)
    if not auth_uid:
        return Response(status_code=401, error_message="Unauthorized Request")
    try:
        with Session() as session:
            user_id = get_user_id(auth_uid, session)
            user = session.query(UserTable).get(user_id)
            # update user with new info
            for key, value in new_user_info:
                setattr(user, key, value)
            # UserTable[user] = new_user_info.dict()
            session.commit()
            return Response(body={"message": "user update succeessful"})
    except Exception as e:
        print(e)
        return Response(status_code=500, error_message=e)
    
@app.patch("/user")
async def update_user(new_user_info: PatchUserSchema, authorization: str = Header(...)):
    """
    Recieves updated user data - specifically team related for now
    Updates database
    Returns success message
    """
    # confirm data coming from valid user
    auth_uid = validate_user_token(authorization)
    if not auth_uid:
        return Response(status_code=401, error_message="Unauthorized Request")
    try:
        print(new_user_info)
        filtered_new_user_info = new_user_info.todict()
        print(filtered_new_user_info)
        with Session() as session:
            user_id = get_user_id(auth_uid, session)
            user = session.query(UserTable).get(user_id)
            # pdb.set_trace()
            # update user with new info
            for key in filtered_new_user_info:
                    setattr(user, key, filtered_new_user_info[key])
            # UserTable[user] = new_user_info.dict()
            session.commit()
            return Response(body={"message": "user update succeessful"})
    except Exception as e:
        print(e)
        return Response(status_code=500, error_message=e)


@app.post("/ergImage")
async def create_extract_and_process_ergImage(ergImg: UploadFile = File(...)):
    """
    Receives UploadFile containing photo of erg screen,
    sends image to Textract for OCR, processes raw result
    Returns processed data
    """
    try:
        tinit = datetime.now()
        print("running ergImage", tinit)
        image_bytes = ergImg.file.read()
        filename = ergImg.filename
        ocr_data: OcrDataReturn = get_processed_ocr_data(filename, image_bytes)
        t4 = datetime.now()
        upload_blob("erg_memory_screen_photos", image_bytes, ocr_data["photo_hash"])
        t5 = datetime.now()
        d3 = t5 - t4
        print("Time to add blob", d3)
        tf = datetime.now()
        dtot = tf - tinit
        print("TOTAL TIME", dtot)
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
            workouts_processed: List[WorkoutLogSchema] = convert_class_instances_to_dicts(
                workouts
            )
            print(workouts_processed)
            return Response(body={"workouts": workouts_processed})
        except Exception as e:
            print(e)
            return Response(status_code=500, error_message=str(e))


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
    split_var = calculate_split_var(workoutData.tableMetrics)
    watts = calculate_watts(workoutData.tableMetrics[0]["split"])
    calories = calculate_cals(workoutData.tableMetrics[0]["time"], watts)
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
                heart_rate = workoutData.tableMetrics[0]["heartRate"],
                split_variance = split_var,
                watts = watts,
                cal = calories,
                image_hash=workoutData.photoHash,
                subworkouts=subworkouts_json,
                comment=workoutData.woMetaData["comment"],
                # TODO: add postToTeam to woMeetaData on react side
                post_to_team = workoutData.woMetaData['postToTeam']
            )

            # use sqlAlchemy to add entryy to db
            session.add(workout_entry)
            session.commit()
            return Response(body={"message": "workout posted successfully"})
        except Exception as e:
            return Response(status_code=500, error_message=e)


@app.delete("/workout/{workout_id}")
async def delete_workout(workout_id: int, authorization: str = Header(...)):
    """
    Receives workout id
    Deletes entry in workout_log with matching id
    Returns success message
    """
    # confirm data coming from valid user
    auth_uid = validate_user_token(authorization)
    if not auth_uid:
        return Response(status_code=401, error_message="Unauthorized Request")
    with Session() as session:
        try:
            entry = session.query(WorkoutLogTable).get(workout_id)
            session.delete(entry)
            session.commit()
            return Response(body={"message": "delete successful"})
        except Exception as e:
            return Response(status_code=500, error_message=e)


@app.get("/team")
async def read_team(authorization: str = Header(...)):
    """
    Receives userToken 
    Uses token to get user_id, queries user table for team_id
    returns: if user is on team - info for team matching team_id + if admin 
    """
    # pdb.set_trace()
    auth_uid = validate_user_token(authorization)
    if not auth_uid:
        return Response(status_code=401, error_message="Unauthorized Request")
    try:
        with Session() as session:
            user_id = get_user_id(auth_uid, session)
            user_info = session.query(UserTable).get(user_id).__dict__
            # pdb.set_trace()
            if user_info['team']:
                team_info = session.query(TeamTable).get(user_info['team']).__dict__
                admin = user_info['team_admin']
                return Response(body={'team_member': True, 'team_info': team_info, 'team_admin': admin})
            else:
                return Response(body={'team_member' : False})     
    except Exception as e:
        print(e)
        return Response(status_code=500, error_message=e)
    

@app.post("/team")
async def write_team(teamData: PostTeamDataSchema, authorization: str = Header(...)):
    """
    Receives userToken, teamName, teamCode
    Adds entry to Team Table (name and code), gets teamID
    Adds teamID to team_id col for user  associated with userToken AND changes team_admin val to True
    Returns team name, [V2 - all workouts for team] 
    """
    auth_uid = validate_user_token(authorization)
    if not auth_uid:
        return Response(status_code=401, error_message="Unauthorized Request")
    try:
        with Session() as session:
            # Query to check if a team already exists - only needed in dev
            new_team_id = session.query(TeamTable.team_id).filter(
                TeamTable.team_name == teamData.teamName,
                TeamTable.team_code == teamData.teamCode
                ).first()[0]
            if not new_team_id: 
                #add new team to team table
                team_entry = TeamTable(
                    team_name = teamData.teamName,
                    team_code = teamData.teamCode
                )
                session.add(team_entry)
                session.commit()
                print('new team created')
                new_team_id = team_entry.team_id
            #update user's info
            user_id = get_user_id(auth_uid, session)
            user = session.query(UserTable).get(user_id)
            user_patch = {"team": new_team_id,"team_admin": True }
            for key in user_patch:
                setattr(user, key, user_patch[key])
            session.commit()
            return Response(body={'team_id':new_team_id, 'team_name':teamData.teamName})
    except Exception as e:
        print(e)
        return Response(status_code=500, error_message=e)

@app.patch('/jointeam')   
async def write_join_team(teamData: PostTeamDataSchema, authorization: str = Header(...)):
    '''
    Receives userToken + team_name + team_code
    Gets id for team matching name and code
    Posts id into team col of user 
    Returns confirmation
    '''
    auth_uid = validate_user_token(authorization)
    if not auth_uid:
        return Response(status_code=401, error_message="Unauthorized Request")
    try:
        with Session() as session:
            # Query to check if a team already exists - only needed in dev
            team_id_result = session.query(TeamTable.team_id).filter(
                TeamTable.team_name == teamData.teamName,
                TeamTable.team_code == teamData.teamCode
                ).first()
            team_id = team_id_result[0] if team_id_result else None
            if not team_id:
                return Response(status_code=404, error_message='no team matching submitted credentials')
            user_id = get_user_id(auth_uid, session)
            user = session.query(UserTable).get(user_id)
            # update user with team id
            setattr(user, 'team', team_id)
            # UserTable[user] = new_user_info.dict()
            session.commit()
            return Response(body={"message": "user update succeessful - team joined", "team_id":team_id})   
    except Exception as e:
        print(e)
        return Response(status_code=500, error_message=e)


@app.get('/teamlog')
async def read_teamlog(authorization: str = Header(...)):
    """
    Receives userToken
    Gets teamID for user
    Gets teamMembers for team matching teamID
    Gets all workouts from WorkoutLogTable done by teamMembers that chose to postToTeam
    Returns team workouts
    """
    #check authorized request
    auth_uid = validate_user_token(authorization)
    if not auth_uid:
        return Response(status_code=401, error_message="Unauthorized Request")
    # get user_ids for team members
    try:
        with Session() as session:
            user_id = get_user_id(auth_uid, session)
            team_id = session.query(UserTable.team).filter_by(user_id=user_id).first()[0]
            team_members = session.query(UserTable).filter(UserTable.team == team_id).all()
            # get workouts for team members where post_to_team == True
            team_workouts = session.query(WorkoutLogTable).filter(
                # WorkoutLogTable.user_id.in_([member[0] for member in team_members]),
                WorkoutLogTable.user_id.in_([athlete.user_id for athlete in team_members]),
                WorkoutLogTable.post_to_team == True
            ).all()
            workouts_processed: List[WorkoutLogSchema] = convert_class_instances_to_dicts(
                team_workouts
            )
            team_members_as_dicts = convert_class_instances_to_dicts(team_members)
            team_workouts_complete = add_user_info_to_workout(workouts_processed, team_members_as_dicts) 
            print(team_workouts_complete)
            return Response(body={"team_workouts": team_workouts_complete})
    except Exception as e:
        print(e)
        return Response(status_code=500, error_message=e)
    

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
