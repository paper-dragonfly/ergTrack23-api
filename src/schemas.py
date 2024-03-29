from pydantic import BaseModel, validator
from typing import Optional, List, Union
from fastapi import UploadFile, Form, File
from datetime import date


# Incoming post/put schema
class PostErgImageSchema(BaseModel):
    photo1: UploadFile = File(...) 
    photo2: Optional[UploadFile]  
    photo3: Optional[UploadFile] 
    


class PostWorkoutSchema(BaseModel):
    woMetaData: dict
    tableMetrics: List[dict]
    photoHash: List[str]
    varInts: Optional[List[dict]] = None 


class PostWorkoutSchema2(BaseModel):
    entryMethod: str = (Form(...),)
    workoutType: str = (Form(...),)
    workoutLength: Optional[str] = (Form(None),)
    customLength: Optional[str] = (Form(None),)
    subWorkouts: Optional[str] = (Form(None),)
    ergImg: Optional[UploadFile] = File(None)


class PutUserSchema(BaseModel):
    user_name: str
    email: str
    country: Optional[str] = None
    sex: Optional[str] = None
    dob: Optional[str] = None
    weight_class: Optional[str] = None
    para_class: Optional[str] = None


class PatchUserSchema(BaseModel):
    team: Optional[int]
    team_admin: Optional[bool] 
    user_name: Optional[str]
    email: Optional[str]
    country: Optional[str] 
    sex: Optional[str] 
    dob: Optional[str] 
    weight_class: Optional[str] 
    para_class: Optional[str] 

    def todict(self) -> dict:
        filtered_new_user_info = {key: value for key, value in vars(self).items() if value is not None}
        if "team" not in filtered_new_user_info:
            filtered_new_user_info['team'] = None 
        return filtered_new_user_info

class PostFeedbackSchema(BaseModel):
    feedbackCategory: str
    comment: str

class PostTeamDataSchema(BaseModel):
    teamName: str
    teamCode: str

## function return schemas
class CleanMetaReturn(BaseModel):
    wo_name: str
    total_type: Optional[str]
    wo_date: str
    total_val: Optional[str]


class WorkoutDataReturn(BaseModel):
    time: List[str]
    meter: List[str]
    split: List[str]
    sr: List[str]
    hr: List[str] = None

class RestInfoSchema(BaseModel):
    time: List[str]
    meter: List[int]
    
class OcrDataReturn(BaseModel):
    workout_meta: CleanMetaReturn
    workout_data: WorkoutDataReturn
    photo_hash: List[str]
    rest_info : RestInfoSchema
    

# # API Response Obj - DEPRICATED, use native JSONResponse
# class Response(BaseModel):
#     status_code: int = 200
#     error_message: str = None
#     body: dict = None


# Miscellaneous
 

class WorkoutLogSchema(BaseModel):
    workout_id: int
    user_id: int
    description: str
    date: date
    time: str
    meter: int
    split: str
    stroke_rate: int
    heart_rate: int
    split_variance: float
    watts: int
    cal: int
    image_hash: Optional[str] = None
    subworkouts: List[dict]
    comment: str
    post_to_team: Optional[bool]  

class WorkoutsDTMSchema(BaseModel):
    date: date
    time: int
    meter: int

class CellData(BaseModel):
    row: str
    col: str 
    text: list
    text_ids: list

class LoginRequest(BaseModel):
    email: str

# Exception
class CustomError(Exception):
    def __init__(self, status_code, message):
        self.status_code = status_code
        self.message = message
