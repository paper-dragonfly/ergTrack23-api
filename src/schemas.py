from pydantic import BaseModel, validator 
from typing import Optional
from fastapi import UploadFile, Form, File

class PostWorkoutSchema(BaseModel):  
    entryMethod: str 
    workoutType: str
    workoutLength: Optional[str]
    customLength: Optional[str]
    subWorkouts: Optional[str]
    ergImg:  Optional[UploadFile] 

class PostWorkoutSchema2(BaseModel):
     entryMethod: str=Form(...),
     workoutType: str=Form(...),
     workoutLength: Optional[str]=Form(None),
     customLength: Optional[str]=Form(None),
     subWorkouts: Optional[str]=Form(None),
     ergImg:  Optional[UploadFile] = File(None)