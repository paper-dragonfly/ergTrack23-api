import pdb 
from http import HTTPStatus
from io import BytesIO
from PIL import Image 
from typing import Optional

from fastapi import FastAPI, Request, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware

from src.schemas import PostWorkoutSchema, PostWorkoutSchema2
from  src.classes import Response

app = FastAPI()

origins = [
    "http://localhost:3000"
]
# Add CORS middleware to the app
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def read_health():
    return {"API status": HTTPStatus.OK}

@app.get("/")
async def root(): 
    return {"message": "Hello World"} 
 

@app.post("/workout")
async def create_workout(
     entryMethod: str=Form(...),
     workoutType: str=Form(...),
     workoutLength: Optional[str]=Form(None),
     customLength: Optional[str]=Form(None),
     subWorkouts: Optional[str]=Form(None),
     ergImg:  Optional[UploadFile] = File(None)):
    
    workout_info = {
        'em': entryMethod,
        'wot': workoutType,
        'wol': workoutLength,
        'cl': customLength,
        'swo': subWorkouts,
    }

    if ergImg:  
        byte_array = bytearray(ergImg.file.read())
        pil_image = Image.open(BytesIO(byte_array))
        pil_image.show()

    return Response(body={'message':'successful post to workout', 'workoutinfo':workout_info})

    # capture in formdata from front end 
    # parse formdata and create bytearrary of image 
    # send image bytes to textract 
    # process response  
    # return response 

@app.post("/sandbox")
async def create_sandbox(name: str = Form(...), age: str = Form(...), image: UploadFile = File(...)):
    form_data = {'name': name, 'age':age}
    print(form_data) 
    byte_array = bytearray(image.file.read())
    pil_image = Image.open(BytesIO(byte_array))
    pil_image.show()  
    return Response(body={'message':'success', 'formdata':form_data})