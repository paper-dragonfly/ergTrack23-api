import os
from hashlib import  sha256
import json
from google.cloud import storage
from src.ocr import hit_textract_api

# Specify the path to the folder containing your JPEG images
folder_path = 'ergImages/ergathon23/'

# List all files in the folder
files = os.listdir(folder_path)

# List all jpegs in folder
jpeg_images = [file for file in files if file.lower().endswith('.jpeg') or file.lower().endswith('.jpg')]

def textract_ocr(byte_array, image_hash):
    # Check if image is already in raw_ocr library
    with open("src/rawocr.json", "r") as f:
        raw_ocr_library = json.load(f)
    library_entries = raw_ocr_library.keys()
    # var below used for testing ocr - change to True for Prod
    search_library = True
    # If yes -> grab raw response
    if search_library and image_hash in library_entries:
        # get raw data using image_hash
        raw_textract_resp = raw_ocr_library[image_hash]
        return False
    # If no -> send to textract
    else:
        raw_textract_resp = hit_textract_api(byte_array)
        # save raw_resp to raw_ocr library
        with open("src/rawocr.json", "w") as f:
            raw_ocr_library[image_hash] = raw_textract_resp
            json.dump(raw_ocr_library, f)
    print('ocr complete: ', image_hash)
    return True
    
  
def upload_blob_gcb(bucket_name: str, image_bytes: bytes, image_hash: str) -> None:
    """Uploads erg_image to google cloud bucket if not already stored"""
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(image_hash)
    if blob.exists():
        print("Duplicate: blob already exists in bucket")
    else:
        blob.upload_from_string(image_bytes, "image/jpeg")
        print(f"{image_hash} uploaded to {bucket_name}.")
        
def extract_and_save(image_list, folder_path):
    processed_images = []
    for image_name in image_list:
        image_path = os.path.join(folder_path, image_name)
        with open(image_path, 'rb') as image_file:
            image_bytes = image_file.read()
            # convert bytes to byte array & create image_hash
            byte_array = bytearray(image_bytes)
            image_hash = sha256(byte_array).hexdigest()
            new_img = textract_ocr(byte_array, image_hash)
            if new_img:
                upload_blob_gcb("erg_memory_screen_photos", image_bytes, image_hash)
        processed_images.append(image_name)
    print(processed_images)

extract_and_save(jpeg_images,folder_path)           
        




