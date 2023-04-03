import pdb
from http import HTTPStatus
import json
from io import BytesIO
from PIL import Image
from typing import Optional

from fastapi import FastAPI, Request, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware

from src.schemas import PostWorkoutSchema, PostWorkoutSchema2
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


@app.get("/health")
def read_health():
    return {"API status": HTTPStatus.OK}


@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.post("/workout")
async def create_workout(
    entryMethod: str = Form(...),
    workoutType: str = Form(...),
    workoutLength: Optional[str] = Form(None),
    customLength: Optional[str] = Form(None),
    subWorkouts: Optional[str] = Form(None),
    ergImg: Optional[UploadFile] = File(None),
):
    workout_info = {
        "entry_method": entryMethod,
        "workout_type": workoutType,
        "workout_length": workoutLength,
        "custom_length": customLength,
        "sub_workouts": subWorkouts,
    }
    # pdb.set_trace()
    if ergImg:
        ocr_data = get_processed_ocr_data(ergImg)
    else:
        ocr_data = None

    return Response(
        body={
            "message": "successful post to workout",
            "workoutinfo": workout_info,
            "ocrdata": ocr_data,
        }
    )


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
