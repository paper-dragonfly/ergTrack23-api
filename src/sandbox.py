import json
import pdb
import os
from PIL import Image
from io import BytesIO
from src.ocr import hit_textract_api
from datetime import datetime
from src.ocr import process_raw_ocr

# run all images through textract if not already in rawOCR.json
IMAGE_DIR = "ergImages"


def ocr_all(dir_path=IMAGE_DIR):
    processed_images = []
    image_names = os.listdir(dir_path)
    # Check if image is already in raw_ocr library
    with open("src/rawocr.json", "r") as f:
        raw_ocr_library = json.load(f)
    library_content = raw_ocr_library.keys()
    for image_name in image_names:
        if not image_name in library_content:
            print("not in library", image_name)
            path = IMAGE_DIR + "/" + image_name
            with open(path, "rb") as f:
                image = f.read()
                byte_array = bytearray(image)
            try:
                raw_textract_resp = hit_textract_api(byte_array)
            except Exception as e:
                print(e)
                print("ocr failed for", image_name)
                continue
            with open("src/rawocr.json", "w") as f:
                raw_ocr_library[image_name] = raw_textract_resp
                json.dump(raw_ocr_library, f)
            print("added to lib")
            processed_images.append(image_name)
    return processed_images


def list_library_contents(dir_path=IMAGE_DIR):
    with open("src/rawocr.json", "r") as f:
        raw_ocr_library = json.load(f)
    library_content = raw_ocr_library.keys()
    print(library_content)
    print("library contents", len(library_content))
    print("ergImage", len(os.listdir(dir_path)))


def sort_processable():
    fails = []
    success = []
    with open("src/rawocr.json", "r") as f:
        raw_ocr_library = json.load(f)
    library_content = raw_ocr_library.keys()
    for image in library_content:
        try:
            resp = process_raw_ocr(raw_ocr_library[image], "fakehash")
            if not "workout_data" in resp.keys():
                print("resp has no workout_data")
                fails.append(image)
            else:
                success.append(image)
        except Exception as e:
            print(e)
            fails.append(image)
    print("success", success, len(success))
    print("Fails", fails, len(fails))


fails = [
    "cr_erg05.jpg",
    "cr_erg02.jpg",
    "cr_erg03.jpg",
    "20220701_130356.jpg",
    "20221117_193442.jpg",
    "20220701_135017.jpg",
    "20220701_124122.jpg",
    "20220701_124150.jpg",
    "20220701_130221.jpg",
    "20220701_130328.jpg",
    "IMG_0298(1).JPG",
    "20220910_091104.jpg",
    "IMG_0761.jpg",
    "20220701_142257.jpg",
    "20220910_091506.jpg",
    "IMG_0288.JPG",
    "IMG_0061.JPG",
    "IMG_0312.JPG",
    "IMG_0927.JPG",
    "20220701_132654.jpg",
]


def fails_info(fails):
    fail_errors = []
    with open("src/rawocr.json", "r") as f:
        raw_ocr_library = json.load(f)
    for image in fails:
        try:
            process_raw_ocr(raw_ocr_library[image], "fakehash")
        except Exception as e:
            # print(e)
            fail_errors.append((image, e))
    print("FAILS LIST")
    for tup in fail_errors:
        print(tup)


def inspect_one(image_name):
    with open("src/rawocr.json", "r") as f:
        raw_ocr_library = json.load(f)
    process_raw_ocr(raw_ocr_library[image_name], "fakehash")


## TEST DB
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import yaml
from src.database import WorkoutLogTable
from google.cloud.sql.connector import Connector
from sqlalchemy import (
    Column,
    Integer,
    String,
    Sequence,
    ForeignKey,
    Date,
    Boolean,
    Float,
    create_engine,
)
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.dialects.postgresql import JSON

# define table schema
Base = declarative_base()


class SandwichesRatings(Base):
    __tablename__ = "ratings"

    id = Column(
        Integer,
        Sequence("ratings_id_seq"),
        primary_key=True,
        nullable=False,
        server_default="nextval('ratings_id_seq')",
    )
    name = Column(String, nullable=False)
    origin = Column(String, nullable=False)
    rating = Column(Float, nullable=False)

    def __repr__(self):
        return "<UserTable(id='%s', name='%s',  origin='%s', rating='%s')>" % (
            self.id,
            self.name,
            self.origin,
            self.rating,
        )


# initialize parameters
INSTANCE_CONNECTION_NAME = "ergtracker:us-east1:ergtrack-gc-db"
# DB_USER = "ergtrack-api"
# DB_PASS = "api-pw-05102023"
# DB_NAME = "ergtrack-05102023"

DB_USER = "chef"
DB_PASS = "food"
DB_NAME = "sandwiches"

# initialize Connector object
connector = Connector()


# function to return the database connection object
def getconn():
    conn = connector.connect(
        INSTANCE_CONNECTION_NAME, "pg8000", user=DB_USER, password=DB_PASS, db=DB_NAME
    )
    return conn


# create connection pool with 'creator' argument to our connection object function
pool = create_engine(
    "postgresql+pg8000://",
    creator=getconn,
)
Session = sessionmaker(bind=pool)


def test_conn(pool=pool):
    with pool.connect() as db_conn:
        # query and fetch ratings table
        results = db_conn.execute(text("SELECT * FROM ratings")).fetchall()

        # show results
        for row in results:
            print(row)
        connector.close()


def test_conn_with_session():
    with Session() as session:
        try:
            resp = session.query(SandwichesRatings).all()
            print(resp)
        except Exception as e:
            print(e)


if __name__ == "__main__":
    ## IMPROVE OCR
    # ocr_all()
    # list_library_contents()
    # sort_processable()
    # fails_info(fails)
    # inspect_one("20220701_130356.jpg")

    ## TEST DB
    # test_conn()
    test_conn_with_session()

# def get_processed_ocr_data(erg_photo):
#     # convert bytes to byte array & create photo_hash
#     byte_array = bytearray(erg_photo.file.read())
#     photo_hash = sha256(byte_array).hexdigest()
#     # Check if image is already in raw_ocr library
#     with open("src/rawocr.json", "r") as f:
#         raw_ocr_library = json.load(f)
#     if erg_photo.filename in raw_ocr_library.keys():
#         # If yes -> grab raw response
#         raw_textract_resp = raw_ocr_library[erg_photo.filename]
#     # If no -> create byte array, display img, send to textract
#     else:
#         # open image + send to AWS Textract for OCR extraction
#         pil_image = Image.open(BytesIO(byte_array))
#         pil_image.show()
#         raw_textract_resp = hit_textract_api(byte_array)
#         # TODO create sha256 hash for img and save image to cloud storage
#         # save raw_resp to raw_ocr library + TODO image hash
#         with open("src/rawocr.json", "w") as f:
#             raw_ocr_library[erg_photo.filename] = raw_textract_resp
#             json.dump(raw_ocr_library, f)
#     # TODO return image_hash too
#     return process_raw_ocr(raw_textract_resp, photo_hash)


# ERG_IMAGE_DIRECTORY = "ergImages"
# RAWOCR_LIBRARY = "src/rawocr2.json"
# FAILED_0412 = [
#     "20220701_142257.jpg",
#     "20220701_130328.jpg",
#     "20220701_142153.jpg",
#     "20220701_132843.jpg",
#     "20220701_130254.jpg",
#     "20220701_124150.jpg",
#     "20220701_130356.jpg",
#     "20221117_193442.jpg",
# ]


# def create_image_name_list(path_to_image_directory: str) -> list:
#     files = os.listdir(path_to_image_directory)
#     files = [f for f in files if f.endswith(".jpg") or f.endswith(".png")]
#     print(len(files))
#     return files


# def capture_raw_ocr(rawocr_json_file: str, dir_path: str, images: list):
#     with open(rawocr_json_file, "r") as f:
#         try:
#             raw_ocr_responses = json.loads(f)
#         except:
#             raw_ocr_responses = {}
#     # For each image in ergImages
#     for image in images:
#         if not image in raw_ocr_responses.keys():
#             # read as bytes array
#             path_to_image = dir_path + "/" + image
#             with open(path_to_image, "rb") as img:
#                 image_bytes = img.read()
#             # send bytes array to textract and capture raw response
#             raw_response = hit_textract_api(image_bytes)
#             # add response object to rawocr dict with name as key
#             raw_ocr_responses[image] = raw_response
#     # update rawocr_library
#     with open(rawocr_json_file, "w") as f:
#         json.dump(raw_ocr_responses, f)
#     return raw_ocr_responses


# def open_rawocr2(file_path=RAWOCR_LIBRARY) -> dict:
#     with open(file_path, "r") as f:
#         raw_ocr_responses = json.load(f)
#     return raw_ocr_responses


# # Check how many are missing cell - i.e. didn't run as table
# def count_tabulated(raw_ocr_responses: dict):
#     resp_count = len(raw_ocr_responses)
#     tally = 0
#     fail = []
#     for entry_name in raw_ocr_responses:
#         blocks: list = raw_ocr_responses[entry_name]["Blocks"]
#         if blocks[-1]["BlockType"] in ("CELL", "TABLE_TITLE"):
#             tally += 1
#         else:
#             fail.append(entry_name)
#     success = tally / resp_count * 100
#     print(fail)
#     print(
#         f"Total entries: {resp_count} \n Tabulated: {tally} \n Percent Success: {success}"
#     )
#     return fail


# def display_fails(image_directory: str, failed_images: list):
#     for image in failed_images:
#         path = image_directory + "/" + image
#         with open(path, "rb") as img:
#             byte_array = img.read()
#         pil_image = Image.open(BytesIO(byte_array))
#         pil_image.show()


# def list_entry_blocktypes(raw_ocr_responses: dict, entry_name: str) -> list:
#     blockTypes = []
#     blocks = raw_ocr_responses[entry_name]["Blocks"]
#     for i in range(len(blocks)):
#         if not blocks[i]["BlockType"] in blockTypes:
#             blockTypes.append(blocks[i]["BlockType"])
#     print(blockTypes)
#     return blockTypes


# def list_all_blocktypes(raw_ocr_responses: dict):
#     all_block_types = {}
#     for image in raw_ocr_responses.keys():
#         all_block_types[image] = list_entry_blocktypes(raw_ocr_responses, image)


# ############################################

# # RUN OCR ON ALL IMAGES
# # pdb.set_trace()
# # erg_images = create_image_name_list(ERG_IMAGE_DIRECTORY)
# # raw_ocr_responses = capture_raw_ocr(RAWOCR_LIBRARY, ERG_IMAGE_DIRECTORY, erg_images)
# # failed = count_tabulated(raw_ocr_responses)


# # DISPLAY FAILS
# # display_fails(ERG_IMAGE_DIRECTORY, FAILED_0412)

# # Expolore

# workouts_outgoing_list = [
#     {
#         "workout_id": 1,
#         "date": datetime.date(2022, 7, 1),
#         "meter": 2000,
#         "stroke_rate": 29,
#         "image_hash": None,
#         "comment": None,
#         "time": "8:52.9",
#         "user_id": 1,
#         "description": None,
#         "split": "2:13.2",
#         "interval": False,
#         "subworkouts": '[{"id": "FHoqA2xfnzx7jIJauEDCe", "time": "1:59.3", "distance": 500, "split": "1:59.3", "strokeRate": 32, "heartRate": null}, {"id": "AivW8by5DcQdejTwFvnPD", "time": "2:14.1", "distance": 1000, "split": "2:14.1", "strokeRate": 29, "heartRate": null}, {"id": "NEK2Muzqza9DbL3NIMymn", "time": "2:17.7", "distance": 1500, "split": "2:17.7", "strokeRate": 24, "heartRate": null}, {"id": "vqHzGJt2nYJnP7IVqSFck", "time": "2:21.9", "distance": 2000, "split": "2:21.9", "strokeRate": 31, "heartRate": null}]',
#     },
#     {
#         "workout_id": 2,
#         "date": datetime.date(2022, 1, 28),
#         "meter": 10000,
#         "stroke_rate": 30,
#         "image_hash": None,
#         "comment": None,
#         "time": "41:52.7",
#         "user_id": 1,
#         "description": None,
#         "split": "2:05.6",
#         "interval": False,
#         "subworkouts": '[{"id": "aE3WD-ETaJWB_R9JCFIIL", "time": "1:51.8", "distance": 500, "split": "1:51.8", "strokeRate": 27, "heartRate": null}, {"id": "mArDJJBN4spmD7QoeYwKf", "time": "1:54.4", "distance": 1000, "split": "1:54.4", "strokeRate": 26, "heartRate": null}, {"id": "RG8pxP1EyRIbyF8F4IfKj", "time": "1:54.7", "distance": 1500, "split": "1:54.7", "strokeRate": 27, "heartRate": null}, {"id": "YJ6JRjtTMeNIay6MzHEtv", "time": "2:01.3", "distance": 2000, "split": "2:01.3", "strokeRate": 33, "heartRate": null}, {"id": "ovgAKOnc_TjDIzD2nA8Ao", "time": "2:08.7", "distance": 2500, "split": "2:08.7", "strokeRate": 30, "heartRate": null}, {"id": "vRBk-3yfkzisqkXY0ZinW", "time": "2:14.9", "distance": 3000, "split": "2:14.9", "strokeRate": 35, "heartRate": null}, {"id": "ANhGmhNPqWKsHZtEXo6Jn", "time": "2:10.4", "distance": 3500, "split": "2:10.4", "strokeRate": 34, "heartRate": null}, {"id": "v-x1vx_LAPli58_eHIVjR", "time": "2:20.6", "distance": 4000, "split": "2:20.6", "strokeRate": 28, "heartRate": null}]',
#     },
#     {
#         "workout_id": 8,
#         "date": datetime.date(2022, 7, 1),
#         "meter": 2000,
#         "stroke_rate": 29,
#         "image_hash": "436fc4beb720123fa096cc72ffd95e4038dd157562d6a466199ac0ea2cb2e089",
#         "comment": "sara's 2k",
#         "time": "8:52.9",
#         "user_id": 1,
#         "description": "2000m",
#         "split": "2:13.2",
#         "interval": False,
#         "subworkouts": '[{"id": "Y2DcYttk3uzQcANjrdivP", "time": "1:59.3", "distance": 500, "split": "1:59.3", "strokeRate": 32, "heartRate": null}, {"id": "o2nAZMDb2lIsPL5D1Eb0O", "time": "2:14.1", "distance": 1000, "split": "2:14.1", "strokeRate": 29, "heartRate": null}, {"id": "g5DY-QyqAT7jxNc9HRsmi", "time": "2:17.7", "distance": 1500, "split": "2:17.7", "strokeRate": 24, "heartRate": null}, {"id": "QVsYUycapSsiOVCtpNfMu", "time": "2:21.9", "distance": 2000, "split": "2:21.9", "strokeRate": 31, "heartRate": null}]',
#     },
# ]
