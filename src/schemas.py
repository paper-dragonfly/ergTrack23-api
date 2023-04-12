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
