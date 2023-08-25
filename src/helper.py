import pdb
from typing import Union, List, Tuple, Dict
import json
import math
from src.schemas import WorkoutLogSchema
from google.cloud import storage
from hashlib import sha256
from PIL import Image
from io import BytesIO
from fastapi import File, UploadFile, Form, Header
from datetime import datetime


from src.ocr import hit_textract_api, process_raw_ocr


def get_processed_ocr_data(
    erg_photo_filename: str, image_bytes: bytes
) -> Tuple[Dict, str]:
    """
    Receives: erg image filename & bytes
    Get raw_ocr (retrieve from library or from AWS Textract) and process
    Returns: processed workout data
    """
    t1 = datetime.now()
    # convert bytes to byte array & create photo_hash
    byte_array = bytearray(image_bytes)
    photo_hash = sha256(byte_array).hexdigest()
    print("photoHash", photo_hash)
    # Check if image is already in raw_ocr library
    with open("src/rawocr.json", "r") as f:
        raw_ocr_library = json.load(f)
    library_entries = raw_ocr_library.keys()
    # var below used for testing ocr - change to True for Prod
    search_library = True
    # If yes -> grab raw response
    if search_library and erg_photo_filename in library_entries:
        # TODO: change all current images in library to have sha256
        # get raw data using image file_name
        raw_textract_resp = raw_ocr_library[erg_photo_filename]
        t2 = datetime.now()
    elif search_library and photo_hash in library_entries:
        # get raw data using photo_hash
        raw_textract_resp = raw_ocr_library[photo_hash]
        t2 = datetime.now()
    # If no -> create byte array, display img, send to textract
    else:
        # open image (dev only) + send to AWS Textract for OCR extraction
        # pil_image = Image.open(BytesIO(byte_array))
        # pil_image.show()
        raw_textract_resp = hit_textract_api(byte_array)
        t2 = datetime.now()
        d1 = t2 - t1
        print("Time for Textract to complete OCR", d1)
        # TODO create sha256 hash for img and save image to cloud storage
        # save raw_resp to raw_ocr library
        with open("src/rawocr.json", "w") as f:
            # TODO: delete row below
            # raw_ocr_library[erg_photo_filename] = raw_textract_resp
            raw_ocr_library[photo_hash] = raw_textract_resp
            json.dump(raw_ocr_library, f)
    # TODO return image_hash too
    processed_data = process_raw_ocr(raw_textract_resp, photo_hash)
    t3 = datetime.now()
    d2 = t3 - t2
    print("Time to process raw data", d2)
    return processed_data


def upload_blob(bucket_name: str, image_bytes: bytes, image_hash: str) -> None:
    """Uploads erg_image to google cloud bucket if not already stored"""
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(image_hash)
    if blob.exists():
        print("Duplicate: blob already exists in bucket")
    else:
        blob.upload_from_string(image_bytes, "image/jpeg")
        print(f"{image_hash} uploaded to {bucket_name}.")


def process_outgoing_workouts(workouts: List[WorkoutLogSchema]) -> List[dict]:
    """Reformat workouts retrieved by sqlAlchemy query from list of class instances to list of dicts"""
    # converts list of class instances into list of dictionaries
    workouts_outgoing_list = []
    for wo in workouts:
        wo_dict = {k: v for k, v in wo.__dict__.items() if not k.startswith("_")}
        workouts_outgoing_list.append(wo_dict)
    return workouts_outgoing_list


def duration_to_seconds(duration:str) -> float:
    time_components = duration.split(':')
    time_components = [float(item) for item in time_components]
    seconds = 0
    
    seconds = time_components.pop(); 
    if len(time_components):
        minutes = time_components.pop()
        seconds += minutes * 60
    
    if len(time_components):
        hour = time_components.pop()
        seconds += hour * 3600
    
    return seconds


def calculate_watts(split: str) -> int:
    pace = duration_to_seconds(split)/500
    watts = math.ceil(2.8/pace**3)
    return watts


def calculate_cals(time: str, watts: float) -> int:
    time_hour = duration_to_seconds(time)/3600
    cal = math.ceil(watts/1000 * time_hour * 860 * 4 + 300)
    return cal

def insert_every_n_indices(lst, item, n):
    for i in range(len(lst) // n):
        index = (i + 1) * n + i
        lst.insert(index, item)

def calculate_split_var(workout_metrics):
    #get split for each subworkout
    splits = []
    for i in range(1,len(workout_metrics)):
        split_sec = duration_to_seconds(workout_metrics[i]['split'])
        splits.append(split_sec)
    if not splits:
        return 0
    split_var = round(max(splits) - min(splits),1)
    print('split_var: ', split_var)
    return split_var
    