from pydantic import BaseModel, validator
from typing import Optional, List
from fastapi import UploadFile, Form, File
from datetime import date


# Incoming post schema
class PostWorkoutSchema(BaseModel):
    woMetaData: dict
    tableMetrics: List[dict]
    photoHash: str


class PostWorkoutSchema2(BaseModel):
    entryMethod: str = (Form(...),)
    workoutType: str = (Form(...),)
    workoutLength: Optional[str] = (Form(None),)
    customLength: Optional[str] = (Form(None),)
    subWorkouts: Optional[str] = (Form(None),)
    ergImg: Optional[UploadFile] = File(None)


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


class OcrDataReturn(BaseModel):
    workout_meta: CleanMetaReturn
    workout_data: WorkoutDataReturn
    photo_hash: str


# API Response Obj
class Response(BaseModel):
    status_code: int = 200
    error_message: str = None
    body: dict = None


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
    image_hash: Optional[str] = None
    subworkouts: List[dict]
    comment: str


class CustomError(Exception):
    pass
