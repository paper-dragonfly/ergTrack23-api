import json
import pdb
from PIL import Image
from io import BytesIO
from src.ocr import hit_textract_api, process_raw_ocr


def get_processed_ocr_data(erg_photo):
    # Check if image is already in raw_ocr library
    with open("src/rawocr.json", "r") as f:
        raw_ocr_library = json.load(f)
    if erg_photo.filename in raw_ocr_library.keys():
        # If yes -> grab raw response
        raw_textract_resp = raw_ocr_library[erg_photo.filename]
    # If no -> create byte array and send to textract
    else:
        # convert bytes to byte array & open image
        byte_array = bytearray(erg_photo.file.read())
        pil_image = Image.open(BytesIO(byte_array))
        pil_image.show()
        # pdb.set_trace()
        raw_textract_resp = hit_textract_api(byte_array)
        # save raw_resp to raw_ocr library
        with open("src/rawocr.json", "w") as f:
            raw_ocr_library[erg_photo.filename] = raw_textract_resp
            json.dump(raw_ocr_library, f)
    return process_raw_ocr(raw_textract_resp)
