import json
import pdb
import os
from PIL import Image
from io import BytesIO
from src.ocr import hit_textract_api


ERG_IMAGE_DIRECTORY = "ergImages"
RAWOCR_LIBRARY = "src/rawocr2.json"
FAILED_0412 = [
    "20220701_142257.jpg",
    "20220701_130328.jpg",
    "20220701_142153.jpg",
    "20220701_132843.jpg",
    "20220701_130254.jpg",
    "20220701_124150.jpg",
    "20220701_130356.jpg",
    "20221117_193442.jpg",
]


def create_image_name_list(path_to_image_directory: str) -> list:
    files = os.listdir(path_to_image_directory)
    files = [f for f in files if f.endswith(".jpg") or f.endswith(".png")]
    print(len(files))
    return files


def capture_raw_ocr(rawocr_json_file: str, dir_path: str, images: list):
    with open(rawocr_json_file, "r") as f:
        try:
            raw_ocr_responses = json.loads(f)
        except:
            raw_ocr_responses = {}
    # For each image in ergImages
    for image in images:
        if not image in raw_ocr_responses.keys():
            # read as bytes array
            path_to_image = dir_path + "/" + image
            with open(path_to_image, "rb") as img:
                image_bytes = img.read()
            # send bytes array to textract and capture raw response
            raw_response = hit_textract_api(image_bytes)
            # add response object to rawocr dict with name as key
            raw_ocr_responses[image] = raw_response
    # update rawocr_library
    with open(rawocr_json_file, "w") as f:
        json.dump(raw_ocr_responses, f)
    return raw_ocr_responses


def open_rawocr2(file_path=RAWOCR_LIBRARY) -> dict:
    with open(file_path, "r") as f:
        raw_ocr_responses = json.load(f)
    return raw_ocr_responses


# Check how many are missing cell - i.e. didn't run as table
def count_tabulated(raw_ocr_responses: dict):
    resp_count = len(raw_ocr_responses)
    tally = 0
    fail = []
    for entry_name in raw_ocr_responses:
        blocks: list = raw_ocr_responses[entry_name]["Blocks"]
        if blocks[-1]["BlockType"] in ("CELL", "TABLE_TITLE"):
            tally += 1
        else:
            fail.append(entry_name)
    success = tally / resp_count * 100
    print(fail)
    print(
        f"Total entries: {resp_count} \n Tabulated: {tally} \n Percent Success: {success}"
    )
    return fail


def display_fails(image_directory: str, failed_images: list):
    for image in failed_images:
        path = image_directory + "/" + image
        with open(path, "rb") as img:
            byte_array = img.read()
        pil_image = Image.open(BytesIO(byte_array))
        pil_image.show()


def list_entry_blocktypes(raw_ocr_responses: dict, entry_name: str) -> list:
    blockTypes = []
    blocks = raw_ocr_responses[entry_name]["Blocks"]
    for i in range(len(blocks)):
        if not blocks[i]["BlockType"] in blockTypes:
            blockTypes.append(blocks[i]["BlockType"])
    print(blockTypes)
    return blockTypes


def list_all_blocktypes(raw_ocr_responses: dict):
    all_block_types = {}
    for image in raw_ocr_responses.keys():
        all_block_types[image] = list_entry_blocktypes(raw_ocr_responses, image)


############################################

# RUN OCR ON ALL IMAGES
# pdb.set_trace()
# erg_images = create_image_name_list(ERG_IMAGE_DIRECTORY)
# raw_ocr_responses = capture_raw_ocr(RAWOCR_LIBRARY, ERG_IMAGE_DIRECTORY, erg_images)
# failed = count_tabulated(raw_ocr_responses)


# DISPLAY FAILS
# display_fails(ERG_IMAGE_DIRECTORY, FAILED_0412)

# Expolore
