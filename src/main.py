import pdb
from http import HTTPStatus
import json
from io import BytesIO
from typing import Optional, List, Union
import time
import yaml
from datetime import datetime, date
import os
import threading
import structlog
import uuid

from fastapi import FastAPI, Request, File, UploadFile, Form, Header
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
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
    PutUserSchema,
    PatchUserSchema,
    PostTeamDataSchema,
    PostFeedbackSchema,
    PostErgImageSchema,
    LoginRequest,
    CustomError
)
from src.utils import (
    create_encrypted_token,
    validate_user_token,
    get_user_id,
    InvalidTokenError,
    create_new_auth_uid,
)
from src import utils as u
from src.database import AthleteTable, WorkoutLogTable, TeamTable, FeedbackTable
from src.helper import (
    convert_class_instances_to_dicts,
    upload_blob,
    get_processed_ocr_data,
    calculate_watts,
    calculate_cals,
    calculate_split_var,
    add_user_info_to_workout,
    merge_ocr_data,
    datetime_encoder,
    create_photo_hash
)

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

# Use FastAPI's exception handling middleware to catch CustomError
@app.exception_handler(CustomError)
async def custom_error_handler(request, exc):
    return JSONResponse(status_code=exc.status_code, content={"error_message": exc.message})

# Load config file values
with open("config/config.yaml", "r") as f:
    config_data = yaml.load(f, Loader=yaml.FullLoader)

# set db connection string based on run environment
DEV_ENV = os.getenv("DEV_ENV")
CONN_STR = config_data["db_conn_str"][DEV_ENV]
SECRET_STRING = config_data["SECRET_STRING"]
os.environ["AWS_ACCESS_KEY_ID"] = config_data["AWS_ACCESS_KEY_ID"]
os.environ["AWS_SECRET_ACCESS_KEY"] = config_data["AWS_SECRET_ACCESS_KEY"]

# initialize Firebase Admin SDK
# Note: can either store credentials as environment variable: export GOOGLE_APPLICATION_CREDENTIALS =  'path/to/sercice-account-key.json' OR use path-str
# cred = credentials.Certificate(os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"))
# when no 'cred' given, searches for default
if DEV_ENV != "docker_compose":
    firebase_admin.initialize_app()


# sqlalchemy setup
engine = create_engine(CONN_STR, echo=False)
Session = sessionmaker(bind=engine)

if DEV_ENV == "prod":
    extra_processors = [structlog.processors.JSONRenderer(),
                        u.custom_processor]
else:
    extra_processors = [structlog.dev.ConsoleRenderer()]

structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        ] + extra_processors
)
log = structlog.get_logger()
log.info("API Running")

######  END POINTS ######


@app.get("/health")
def read_health():
    return {"API status": HTTPStatus.OK}


@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.post("/login/")
async def read_login(request: LoginRequest, authorization: str = Header(...)):
    """
    Receives id_token and email
    Validate user with Firebase, add to ergTrack db if new, generate encrypted token
    Return encrypted token
    """
    log.info("Started", endpoint="login", method="post")
    try:
        # hack fix added delay - TODO find better  solution
        # time.sleep(2.0)
        tinit = datetime.now()
        email = request.email
        team_id = None
        if DEV_ENV == "prod":
            id_token = authorization.split(" ")[1]
            decoded_token = auth.verify_id_token(id_token)
        else:
            log.info("logging in without firebase authentication", email=email)

        # check if user in ergtrack db, if not add user
        with Session() as session:
            try:
                existing_user = (
                    session.query(AthleteTable).filter_by(email=email).one_or_none()
                )
                if existing_user:
                    auth_uid = existing_user.auth_uid
                    team_id = existing_user.team
                # create new user
                else:
                    if DEV_ENV == "prod":
                        auth_uid = decoded_token["uid"]
                        username = decoded_token.get("name") if decoded_token.get("name") else email.split('@')[0]
                    else:
                        auth_uid = create_new_auth_uid()
                        username = email.split('@')[0]
                        
                    new_user = AthleteTable(
                        auth_uid=auth_uid,
                        user_name=username,
                        email=email,
                    )
                    session.add(new_user)
                    session.commit()
            except Exception as e:
                log.error(
                    f"cannot validate user or cannot add user to db: {email}",
                    error_message=str(e),
                )
                return JSONResponse(status_code=500, content={"error_message":str(e)})
        encrypted_token = create_encrypted_token(auth_uid)
        tf = datetime.now()
        dur = tf - tinit
        log.info("Time to login", login_dur=dur)
        json_encrypted_token = jsonable_encoder(encrypted_token)
        return JSONResponse(content={"user_token": json_encrypted_token, "team_id": team_id})
    except auth.InvalidIdTokenError as err:
        log.error("Token Invalid ", error_message=str(err))
        # Token invalid
        return JSONResponse(status_code=404, content={'error_message':f"Token invalid: {str(err)}"})
    except Exception as e:
        log.error(f'user: {email}', str(e))
        return JSONResponse(
            status_code=400, content={'error_message':"no token recieved or other issue"}
        )


@app.get("/user")
async def read_user(authorization: str = Header(...)):
    """
    Recieves user_id
    Returns all data from AthleteTable for that user
    """
    log.info("Started", endpoint="user", method="get")
    try:
        # confirm data coming from valid user
        auth_uid = validate_user_token(authorization)
        with Session() as session:
            user_id = get_user_id(auth_uid, session)
            user = session.query(AthleteTable).get(user_id)
            user_info = {
                column.name: getattr(user, column.name)
                for column in AthleteTable.__table__.columns
            }
            json_user_info = jsonable_encoder(user_info)
            return JSONResponse(content=json_user_info)
    except InvalidTokenError as e:
        log.error("Invalid Token Error", error_message=str(e))
        return JSONResponse(status_code=404, content={"error_message":str(e)})
    except Exception as e:
        log.error(f"GET user Error, uid={user_id}", error_message=str(e))
        return JSONResponse(status_code=500, content={"error_message":str(e)})


@app.put("/user")
async def update_user(new_user_info: PutUserSchema, authorization: str = Header(...)):
    """
    Recieves updated user data
    Updates database
    Returns success message
    """
    log.info("Started", endpoint="user", method="put")
    try:
        # confirm data coming from valid user
        auth_uid = validate_user_token(authorization)
        with Session() as session:
            user_id = get_user_id(auth_uid, session)
            user = session.query(AthleteTable).get(user_id)
            # update user with new info
            for key, value in new_user_info:
                #avoid bug -> '' != datetime value
                if key == 'dob' and not value:
                    value = None
                setattr(user, key, value)
            # AthleteTable[user] = new_user_info.dict()
            session.commit()
            return JSONResponse(content={"message": "user update successful"})
    except InvalidTokenError as e:
        log.error("Invalid Token Error", error_message=str(e))
        return JSONResponse(status_code=404, content={"error_message":str(e)})
    except Exception as e:
        log.error(f"PUT user Error, uid={user_id}", error_message=str(e))
        return JSONResponse(status_code=500, content={"error_message":str(e)})


@app.patch("/user")
async def patch_user(
    new_user_info: PatchUserSchema,
    authorization: str = Header(...),
    userId: Union[int, None] = None,
):
    """
    Recieves updated user data - specifically team related for now
    Updates database
    Returns success message
    """
    log.info("Started", endpoint="user", method="patch")
    # confirm data coming from valid user
    try:
        auth_uid = validate_user_token(authorization)
        filtered_new_user_info = new_user_info.todict()
        with Session() as session:
            # should I add security layere that confirms  auth_uid matches admin if trying to edit another users info?
            user_id = userId if userId else get_user_id(auth_uid, session)
            user = session.query(AthleteTable).get(user_id)
            # update user with new info
            for key in filtered_new_user_info:
                setattr(user, key, filtered_new_user_info[key])
            # AthleteTable[user] = new_user_info.dict()
            session.commit()
            return JSONResponse(content={"message": "user update succeessful"})
    except InvalidTokenError as e:
        log.error("Invalid Token Error", error_message=str(e))
        return JSONResponse(status_code=404, content={"error_message":str(e)})
    except Exception as e:
        log.error(f"PATCH user Error, uid={user_id}", error_message=str(e))
        return JSONResponse(status_code=500, content={"error_message":str(e)})


@app.post("/ergImage")
def create_extract_and_process_ergImage(
    photo1: UploadFile,
    photo2: Union[UploadFile, None] = None,
    photo3: Union[UploadFile, None] = None,
    numSubs: Union[int, None] = None,
    authorization: str = Header(...),
):
    """
    Receives UploadFile containing photo of erg screen,
    sends image to Textract for OCR, processes raw result, save img gcs bucket
    Returns processed data
    """
    log.info("Started", endpoint="ergImage", method="post")
    try:
        auth_uid = validate_user_token(authorization)
        with Session() as session:
            athlete = session.query(AthleteTable).filter_by(auth_uid=auth_uid).first()
            athlete.last_post = date.today().strftime('%Y-%m-%d')
            session.commit() 
        with Session() as session: 
            tinit = datetime.now()
            unmerged_ocr_data = []
            ergImgs = [photo for photo in (photo1, photo2, photo3) if photo]
            for img in ergImgs:
                filename = img.filename
                image_bytes = img.file.read()
                photo_hash = create_photo_hash(image_bytes, auth_uid, session)
                # 1. Send photo to Textract (or get raw_blob from library) 
                # 2. Process raw data to get processed workout and metadata 
                ocr_data: OcrDataReturn = get_processed_ocr_data(image_bytes, photo_hash)
                upload_blob_thread = threading.Thread(
                    target=upload_blob,
                    args=("erg_memory_screen_photos", image_bytes, photo_hash),
                    name=f"UploadBlobThread_{filename}",
                )
                upload_blob_thread.start()
                unmerged_ocr_data.append(ocr_data)
            if len(unmerged_ocr_data) == 1:
                tf = datetime.now()
                dtot = tf - tinit
                log.info("TOTAL TIME", total_dur=dtot)
                json_compatable_ocr_data = jsonable_encoder(vars(unmerged_ocr_data[0]))
                return JSONResponse(content=json_compatable_ocr_data)
            final_ocr_data = merge_ocr_data(unmerged_ocr_data, numSubs)
            dtot = datetime.now() - tinit
            log.info("TOTAL TIME", total_dur=dtot)
            json_compatable_ocr_data = jsonable_encoder(vars(final_ocr_data))
            return JSONResponse(content=json_compatable_ocr_data)
    except InvalidTokenError as e:
        log.error("Invalid Token Error", error_message=str(e))
        return JSONResponse(status_code=404, content={"error_message":str(e)})
    except Exception as e:
        # save image to unprocessable_erg_screens bucket
        upload_blob_thread = threading.Thread(
            target=upload_blob,
            args=("unprocessable_erg_screens", image_bytes, photo_hash),
            name=f"UploadBlobThread_{filename}",
        )
        upload_blob_thread.start()

        log.error(f"/ergImage exception, uid={user_id}", error_message=str(e))
        # pdb.set_trace() 
        raise e


@app.get("/workout")
async def read_workout(authorization: str = Header(...)):
    """Get all workout data for user"""
    log.info("Started", endpoint="workout", method="get")
    try:
        auth_uid = validate_user_token(authorization)
        with Session() as session:
            user_id = get_user_id(auth_uid, session)
            workouts = session.query(WorkoutLogTable).filter_by(user_id=user_id).all()
            workouts_processed = convert_class_instances_to_dicts(workouts)
            return JSONResponse(content={"workouts": workouts_processed})
    except InvalidTokenError as e:
        log.error("Invalid Token Error", error_message=str(e))
        return JSONResponse(status_code=404, content={"error_message":str(e)})
    except Exception as e:
        log.error(f"GET workout Error, uid={user_id}", error_message=str(e))
        return JSONResponse(status_code=500, content={"error_message":str(e)})


@app.post("/workout")
async def create_workout(
    workoutData: PostWorkoutSchema, authorization: str = Header(...)
):
    """
    Receives: workout data and id_token
    Add workout data to ergTrack db
    Retruns: success message
    """
    log.info("Started", endpoint="workout", method="post")
    # confirm data coming from valid user
    with Session() as session:
        try:
            auth_uid = validate_user_token(authorization)
            split_var = calculate_split_var(workoutData.tableMetrics)
            watts = calculate_watts(workoutData.tableMetrics[0]["split"])
            calories = calculate_cals(workoutData.tableMetrics[0]["time"], watts)
            # get user_id
            user_id = get_user_id(auth_uid, session)
            # create data entry (WorkoutLogTable  instance)
            subworkouts_json = json.dumps(workoutData.tableMetrics[1:])
            photo_hash_joined = "&nextphotohash&".join(workoutData.photoHash)
            workout_entry = WorkoutLogTable(
                user_id=user_id,
                description=workoutData.woMetaData["workoutName"],
                date=workoutData.woMetaData["workoutDate"],
                time=workoutData.tableMetrics[0]["time"],
                meter=workoutData.tableMetrics[0]["distance"],
                split=workoutData.tableMetrics[0]["split"],
                stroke_rate=workoutData.tableMetrics[0]["strokeRate"],
                heart_rate=workoutData.tableMetrics[0]["heartRate"],
                split_variance=split_var,
                watts=watts,
                cal=calories,
                image_hash=photo_hash_joined,
                subworkouts=subworkouts_json,
                comment=workoutData.woMetaData["comment"],
                post_to_team=workoutData.woMetaData["postToTeam"],
            )

            # use sqlAlchemy to add entry to db
            session.add(workout_entry)
            session.commit()
            return JSONResponse(content={"message": "workout posted successfully"})
        except InvalidTokenError as e:
            log.error("Invalid Token Error", error_message=str(e))
            return JSONResponse(status_code=404, content={"error_message":str(e)})
        except Exception as e:
            log.error(f"POST workout Error, uid={user_id}", error_message=str(e))
            return JSONResponse(status_code=500, content={"error_message":str(e)})


@app.delete("/workout/{workout_id}")
async def delete_workout(workout_id: int, authorization: str = Header(...)):
    """
    Receives workout id
    Deletes entry in workout_log with matching id
    Returns success message
    """
    log.info("Started", endpoint="workout", method="delete")
    # confirm data coming from valid user
    try:
        auth_uid = validate_user_token(authorization)
        with Session() as session:
            user_id = get_user_id(auth_uid, session)
            entry = session.query(WorkoutLogTable).get(workout_id)
            if entry.user_id != user_id:
                return JSONResponse(status_code=401, content={"error_message":"cannot delete other people's workouts"})
            session.delete(entry)
            session.commit()
            return JSONResponse(content={"message": "delete successful"})
    except InvalidTokenError as e:
        log.error("Invalid Token Error", error_message=str(e))
        return JSONResponse(status_code=404, content={"error_message":str(e)})
    except Exception as e:
        log.error(f"DELETE workout Error, uid={user_id}", error_message=str(e))
        return JSONResponse(status_code=500, content={"error_message":str(e)})


@app.get("/team")
async def read_team(authorization: str = Header(...)):
    """
    Receives userToken
    Uses token to get user_id, queries user table for team_id
    returns: if user is on team - info for team matching team_id + if admin
    """
    log.info("Started", endpoint="team", method="get")
    try:
        auth_uid = validate_user_token(authorization)
        with Session() as session:
            user_id = get_user_id(auth_uid, session)
            user_info = session.query(AthleteTable).get(user_id).__dict__
            if user_info["team"]:
                team = session.query(TeamTable).get(user_info["team"])
                team_info = {
                    column.name: getattr(team, column.name)
                    for column in TeamTable.__table__.columns
                }
                admin = user_info["team_admin"]
                return JSONResponse(
                    content={
                        "team_member": True,
                        "team_info": team_info,
                        "team_admin": admin,
                    }
                )
            else:
                return JSONResponse(content={"team_member": False})
    except InvalidTokenError as e:
        log.error("Invalid Token Error", error_message=str(e))
        return JSONResponse(status_code=404, content={"error_message":str(e)})
    except Exception as e:
        log.error(f"GET team Error, uid={user_id}", error_message=str(e))
        return JSONResponse(status_code=500, content={"error_message":str(e)})


@app.post("/team")
async def write_team(teamData: PostTeamDataSchema, authorization: str = Header(...)):
    """
    Receives userToken, teamName, teamCode
    Adds entry to Team Table (name and code), gets teamID
    Adds teamID to team_id col for user  associated with userToken AND changes team_admin val to True
    Returns team name, [V2 - all workouts for team]
    """
    log.info("Started", endpoint="team", method="post")
    try:
        auth_uid = validate_user_token(authorization)
        with Session() as session:
            try:
                # Query to check if the "new" team already exists - only needed in dev, assume in prod no one would create identical teams
                # TODO: does this leave us with the potential for dual admins? ... I think so... does it matter?
                new_team_id = (
                    session.query(TeamTable.team_id)
                    .filter(
                        TeamTable.team_name == teamData.teamName,
                        TeamTable.team_code == teamData.teamCode,
                    )
                    .first()[0]
                )
                if new_team_id:
                    return JSONResponse(
                        status_code=403, error_message="Team already exists"
                    )
            except TypeError:
                # team not in db - add new team to team table
                team_entry = TeamTable(
                    team_name=teamData.teamName, team_code=teamData.teamCode
                )
                session.add(team_entry)
                session.commit()
                log.info("New team created", team_name=teamData.teamName)
                new_team_id = team_entry.team_id
            # update user's info
            user_id = get_user_id(auth_uid, session)
            user = session.query(AthleteTable).get(user_id)
            user_patch = {"team": new_team_id, "team_admin": True}
            for key in user_patch:
                setattr(user, key, user_patch[key])
            session.commit()
            return JSONResponse(
                content={"team_id": new_team_id, "team_name": teamData.teamName}
            )
    except InvalidTokenError as e:
        log.error("Invalid Token Error", error_message=str(e))
        return JSONResponse(status_code=404, content={"error_message":str(e)})
    except Exception as e:
        log.error(f"POST team Error, uid={user_id}", error_message=str(e))
        return JSONResponse(status_code=500, content={"error_message":str(e)})


@app.put("/team/{team_id}")
async def update_team(
    team_id: int, teamData: PostTeamDataSchema, authorization: str = Header(...)
):
    """_summary_

    Args:
        team_id (int):
        teamData (PostTeamDataSchema): team name and team code
        authorization (str, optional): contains userToken -> auth_uid

    Action:
        updates team info

    Returns:
        Confirmation (JSONResponse):
    """
    log.info("Started", endpoint="team", method="put")
    try:
        auth_uid = validate_user_token(authorization)
        with Session() as session:
            user_id = get_user_id(auth_uid, session)
            team = session.query(TeamTable).get(team_id)
            # update user with new info
            team.team_name = teamData.teamName
            team.team_code = teamData.teamCode
            # for key, value in vars(teamData).items():
            #     setattr(team, key, value)
            session.commit()
            return JSONResponse(content={"message": "team update succeessful"})
    except InvalidTokenError as e:
        log.error("Invalid Token Error", error_message=str(e))
        return JSONResponse(status_code=404, content={"error_message":str(e)})
    except Exception as e:
        log.error(f"PUT team Error, uid={user_id}", error_message=str(e))
        return JSONResponse(status_code=500, content={"error_message":str(e)})


@app.patch("/jointeam")
async def write_join_team(
    teamData: PostTeamDataSchema, authorization: str = Header(...)
):
    """
    Receives userToken + team_name + team_code
    Gets id for team matching name and code
    Posts id into team col of user
    Returns confirmation
    """
    log.info("Started", endpoint="jointeam", method="patch")
    try:
        auth_uid = validate_user_token(authorization)
        with Session() as session:
            # Query to check if a team already exists - only needed in dev
            team_id_result = (
                session.query(TeamTable.team_id)
                .filter(
                    TeamTable.team_name == teamData.teamName,
                    TeamTable.team_code == teamData.teamCode,
                )
                .first()
            )
            team_id = team_id_result[0] if team_id_result else None
            if not team_id:
                return JSONResponse(
                    status_code=404,
                    error_message="no team matching submitted credentials",
                )
            user_id = get_user_id(auth_uid, session)
            user = session.query(AthleteTable).get(user_id)
            # update user with team id
            setattr(user, "team", team_id)
            # AthleteTable[user] = new_user_info.dict()
            session.commit()
            return JSONResponse(
                content={
                    "message": "user update successful - team joined",
                    "team_id": team_id,
                }
            )
    except InvalidTokenError as e:
        log.error("Invalid Token Error", error_message=str(e))
        return JSONResponse(status_code=404, content={"error_message":str(e)})
    except Exception as e:
        log.error(f"PATCH jointeam Error, uid={user_id}", error_message=str(e))
        return JSONResponse(status_code=500, content={"error_message":str(e)})


@app.get("/teamlog")
async def read_teamlog(authorization: str = Header(...)):
    """
    Receives userToken
    Gets teamID for user
    Gets teamMembers for team matching teamID
    Gets all workouts from WorkoutLogTable done by teamMembers that chose to postToTeam
    Returns team workouts
    """
    log.info("Started", endpoint="teamlog", method="get")
    try:
        # check authorized request
        auth_uid = validate_user_token(authorization)
        # get user_ids for team members
        with Session() as session:
            user_id = get_user_id(auth_uid, session)
            team_id = (
                session.query(AthleteTable.team).filter_by(user_id=user_id).first()[0]
            )
            team_members = (
                session.query(AthleteTable).filter(AthleteTable.team == team_id).all()
            )
            # get workouts for team members where post_to_team == True
            team_workouts = (
                session.query(WorkoutLogTable)
                .filter(
                    # WorkoutLogTable.user_id.in_([member[0] for member in team_members]),
                    WorkoutLogTable.user_id.in_(
                        [athlete.user_id for athlete in team_members]
                    ),
                    WorkoutLogTable.post_to_team == True,
                )
                .all()
            )
            workouts_processed: List[
                WorkoutLogSchema
            ] = convert_class_instances_to_dicts(team_workouts)
            team_members_as_dicts = convert_class_instances_to_dicts(team_members)
            team_workouts_complete = add_user_info_to_workout(
                workouts_processed, team_members_as_dicts
            )
            return JSONResponse(content={"team_workouts": team_workouts_complete})
    except InvalidTokenError as e:
        log.error("Invalid Token Error", error_message=str(e))
        return JSONResponse(status_code=404, content={"error_message":str(e)})
    except Exception as e:
        log.error(f"GET teamlog Error, uid={user_id}", error_message=str(e))
        return JSONResponse(status_code=500, content={"error_message":str(e)})


@app.get("/teamadmin")
async def read_team_info(authorization: str = Header(...)):
    """
    Receives userToken
    Get user from  userToken, get user team, get team info, get member info
    Returns team info and team members' info
    """
    log.info("Started", endpoint="teamadmin", method="get")
    try:
        # check authorized request
        auth_uid = validate_user_token(authorization)
        with Session() as session:
            user_id = get_user_id(auth_uid, session)
            team_id = (
                session.query(AthleteTable.team).filter_by(user_id=user_id).first()[0]
            )
            team_info_inst = session.query(TeamTable).filter_by(team_id=team_id).first()
            team_info_dict = {
                k: v
                for k, v in team_info_inst.__dict__.items()
                if not k.startswith("_")
            }
            team_members_inst = (
                session.query(AthleteTable).filter(AthleteTable.team == team_id).all()
            )
            team_members = convert_class_instances_to_dicts(team_members_inst)
            return JSONResponse(
                content={
                    "team_info": team_info_dict,
                    "team_members": team_members,
                    "admin_uid": user_id,
                }
            )
    except InvalidTokenError as e:
        log.error("Invalid Token Error", error_message=str(e))
        return JSONResponse(status_code=404, content={"error_message":str(e)})
    except Exception as e:
        log.error(f"GET teamadmin Error, uid={user_id}", error_message=str(e))
        return JSONResponse(status_code=500, content={"error_message":str(e)})


@app.patch("/transferadmin/{new_admin_id}")
async def update_admin(new_admin_id: int, authorization: str = Header(...)):
    """_summary_

    Args:
        new_admin_id (int): user_id for athlete
        authorization (str, optional): _description_. Defaults to Header(...).

    Action:
        switches value of admin for new_admin to true and old admin to falsee
    Returns:
        JSONResponse : success message
    """
    log.info("Started", endpoint="transferadmin", method="patch")
    try:
        auth_uid = validate_user_token(authorization)
        with Session() as session:
            # should I add security layer that confirms  auth_uid matches admin if trying to edit another users info?
            user_id = get_user_id(auth_uid, session)
            old_admin = session.query(AthleteTable).get(user_id)
            new_admin = session.query(AthleteTable).get(new_admin_id)
            setattr(old_admin, "team_admin", False)
            setattr(new_admin, "team_admin", True)
            session.commit()
            return JSONResponse(content={"message": "Update successful"})
    except InvalidTokenError as e:
        log.error("Invalid Token Error", error_message=str(e))
        return JSONResponse(status_code=404, content={"error_message":str(e)})
    except Exception as e:
        log.error(f"PATCH transferadmin Error, uid={user_id}", error_message=str(e))
        return JSONResponse(status_code=500, content={"error_message":str(e)})


# OTHER


@app.post("/feedback")
async def create_feedback(
    feedbackInfo: PostFeedbackSchema, authorization: str = Header(...)
):
    log.info("Started", endpoint="feedback", method="post")
    try:
        auth_uid = validate_user_token(authorization)
        with Session() as session:
            user_id = get_user_id(auth_uid, session)
            entry = FeedbackTable(
                date=date.today(),
                user_id=user_id,
                feedback_type=feedbackInfo.feedbackCategory,
                comment=feedbackInfo.comment,
            )
            session.add(entry)
            session.commit()
            log.info(
                "Feedback submitted",
                fb_type=feedbackInfo.feedbackCategory,
                comment=feedbackInfo.comment,
                user=user_id,
            )
            new_feedback_id = entry.feedback_id
            return JSONResponse(content={new_feedback_id: new_feedback_id})
    except InvalidTokenError as e:
        log.error("Invalid Token Error", error_message=str(e))
        return JSONResponse(status_code=404, content={"error_message":str(e)})
    except Exception as e:
        log.error(f"POST feedback Error, uid={user_id}", error_message=str(e))
        return JSONResponse(status_code=500, content={"error_message":str(e)})


@app.post("/sandbox")
async def create_sandbox(
    name: str = Form(...), age: str = Form(...), image: UploadFile = File(...)
):
    form_data = {"name": name, "age": age}
    print(form_data)
    byte_array = bytearray(image.file.read())
    pil_image = Image.open(BytesIO(byte_array))
    pil_image.show()
    return JSONResponse(content={"message": "success", "formdata": form_data})
