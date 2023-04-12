import pdb
from http import HTTPStatus
import json
from io import BytesIO
from PIL import Image
from typing import Optional

from fastapi import FastAPI, Request, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware

from src.schemas import PostWorkoutSchema
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


@app.post("/ergImage")
async def create_extract_and_process_ergImage(ergImg: UploadFile = File(...)):
    ocr_data = get_processed_ocr_data(ergImg)
    # TODO: if successful -> use cabinet to save Image to cloudStorage
    # TODO: will need to add image_hash to response

    return Response(body=ocr_data)


@app.post("/workout")
async def create_workout(workoutData: PostWorkoutSchema):
    print(workoutData)
    return Response(body={"message": "success  post to workout"})


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
