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
import structlog

from src.schemas import OcrDataReturn, WorkoutDataReturn
from src.ocr import hit_textract_api, process_raw_ocr

log = structlog.get_logger()


def get_processed_ocr_data(
    erg_photo_filename: str, image_bytes: bytes
) -> OcrDataReturn:
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
    library_entries = raw_ocr_library.keys()
    # var below used for testing ocr - change to True for Prod
    search_library = False
    # If yes -> grab raw response
    if search_library and photo_hash in library_entries:
        # get raw data using photo_hash
        raw_textract_resp = raw_ocr_library[photo_hash]
        t2 = datetime.now()
        log.info("Raw OCR from library")
    # If no -> create byte array, display img, send to textract
    else:
        # open image (dev only) + send to AWS Textract for OCR extraction
        # pil_image = Image.open(BytesIO(byte_array))
        # pil_image.show()
        raw_textract_resp = hit_textract_api(byte_array)
        t2 = datetime.now()
        d1 = t2 - t1
        log.info("Time for Textract to complete OCR", duration=d1)
        # save raw_resp to raw_ocr library
        with open("src/rawocr.json", "w") as f:
            raw_ocr_library[photo_hash] = raw_textract_resp
            json.dump(raw_ocr_library, f)
    processed_data = process_raw_ocr(raw_textract_resp, photo_hash)
    t3 = datetime.now()
    d2 = t3 - t2
    log.info("Time to process raw data", process_dur=d2)
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


def merge_ocr_data(unmerged_data: List[OcrDataReturn], numSubs: int) -> OcrDataReturn:
    # Assumptions
    # 1. each photo contains max possible  # undocumented Sub-WOs
    merged_data: OcrDataReturn = unmerged_data[0]

    # Combine photo_hash from all unmerged_data
    photo_hash = [data.photo_hash[0] for data in unmerged_data]
    merged_data.photo_hash = photo_hash

    # Merge WorkoutDataReturn objects
    wo_data: WorkoutDataReturn = merged_data.workout_data

    # add all sub-workouts from middle photos
    # Iterate over all elements in unmerged_data except first and last
    # basically add  data from photo2 in  case with 3 photos
    for data in unmerged_data[1:-1]:
        wo_data.time.extend(data.workout_data.time[1:])
        wo_data.meter.extend(data.workout_data.meter[1:])
        wo_data.split.extend(data.workout_data.split[1:])
        wo_data.sr.extend(data.workout_data.sr[1:])
        wo_data.hr.extend(data.workout_data.hr[1:])

    # add remaining sub-workouts from last photo
    last_subs_idx = -1 * (numSubs % 8)
    wo_data.time.extend(unmerged_data[-1].workout_data.time[last_subs_idx:])
    wo_data.meter.extend(unmerged_data[-1].workout_data.meter[last_subs_idx:])
    wo_data.split.extend(unmerged_data[-1].workout_data.split[last_subs_idx:])
    wo_data.sr.extend(unmerged_data[-1].workout_data.sr[last_subs_idx:])
    wo_data.hr.extend(unmerged_data[-1].workout_data.hr[last_subs_idx:])
    return merged_data


def convert_class_instances_to_dicts(sqlAlchemy_insts: list) -> List[dict]:
    """Reformat response retrieved by sqlAlchemy query from list of class instances to list of dicts"""
    # converts list of class instances -> list of dictionaries
    converted_list = []
    for inst in sqlAlchemy_insts:
        inst_as_dict = {k: v for k, v in inst.__dict__.items() if not k.startswith("_")}
        converted_list.append(inst_as_dict)
    return converted_list


def duration_to_seconds(duration: str) -> float:
    time_components = duration.split(":")
    time_components = [float(item) for item in time_components]
    seconds = 0

    seconds = time_components.pop()
    if len(time_components):
        minutes = time_components.pop()
        seconds += minutes * 60

    if len(time_components):
        hour = time_components.pop()
        seconds += hour * 3600

    return seconds


def calculate_watts(split: str) -> int:
    pace = duration_to_seconds(split) / 500
    watts = math.ceil(2.8 / pace**3)
    return watts


def calculate_cals(time: str, watts: float) -> int:
    time_hour = duration_to_seconds(time) / 3600
    # W -> kW 1 | kWh = 860 kCal | efficiency 25% | just living 300kCal/h
    cal = math.ceil(watts / 1000 * time_hour * 860 * 4 + 300 * time_hour)
    return cal


def insert_every_n_indices(lst, item, n):
    for i in range(len(lst) // n):
        index = (i + 1) * n + i
        lst.insert(index, item)


def calculate_split_var(workout_metrics):
    # get split for each subworkout
    splits = []
    for i in range(1, len(workout_metrics)):
        split_sec = duration_to_seconds(workout_metrics[i]["split"])
        splits.append(split_sec)
    if not splits:
        return 0
    split_var = round(max(splits) - min(splits), 1)
    print("split_var: ", split_var)
    return split_var


def add_user_info_to_workout(workouts: List[dict], members: List[dict]) -> List[dict]:
    members_by_id = {}
    for athlete in members:
        members_by_id[athlete["user_id"]] = athlete

    for i in range(len(workouts)):
        uid = workouts[i]["user_id"]
        workouts[i]["user_name"] = members_by_id[uid]["user_name"]
        workouts[i]["sex"] = members_by_id[uid]["sex"]
        workouts[i]["dob"] = members_by_id[uid]["dob"]
    return workouts
