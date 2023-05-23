import pdb
from typing import Union, List, Tuple, Dict
import json
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
    # Check if image is already in raw_ocr library
    with open("src/rawocr.json", "r") as f:
        raw_ocr_library = json.load(f)
    if erg_photo_filename in raw_ocr_library.keys():
        # If yes -> grab raw response
        raw_textract_resp = raw_ocr_library[erg_photo_filename]
        t2 = datetime.now()
    # If no -> create byte array, display img, send to textract
    else:
        # open image + send to AWS Textract for OCR extraction
        pil_image = Image.open(BytesIO(byte_array))
        pil_image.show()
        raw_textract_resp = hit_textract_api(byte_array)
        t2 = datetime.now()
        d1 = t2 - t1
        print("Time for Textract to complete OCR", d1)
        # TODO create sha256 hash for img and save image to cloud storage
        # save raw_resp to raw_ocr library + TODO image hash
        with open("src/rawocr.json", "w") as f:
            raw_ocr_library[erg_photo_filename] = raw_textract_resp
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
        # pdb.set_trace()
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
