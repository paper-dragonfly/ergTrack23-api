from pydantic import BaseModel, validator
from typing import Optional, List
from fastapi import UploadFile, Form, File


class PostWorkoutSchema(BaseModel):
    nameAndDate: dict
    tableMetrics: List[dict]


class PostWorkoutSchema2(BaseModel):
    entryMethod: str = (Form(...),)
    workoutType: str = (Form(...),)
    workoutLength: Optional[str] = (Form(None),)
    customLength: Optional[str] = (Form(None),)
    subWorkouts: Optional[str] = (Form(None),)
    ergImg: Optional[UploadFile] = File(None)


## return schemas
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
