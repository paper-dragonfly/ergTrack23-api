from starlette.datastructures import UploadFile
from io import BytesIO
import pdb
from google.cloud import storage
from hashlib import sha256


# create a BytesIO object with some test data
with open("ergImages/20220701_130150.jpg", "rb") as f:
    test_data = f.read()
# test_data = b"Hello, world!"
test_file = BytesIO(test_data)

# create a test UploadFile object with the BytesIO object
upload_file = UploadFile(
    test_file,
    filename="test.jpg",
    headers={"content-type": "image/jpeg"},
)


def examine_file(image_file=upload_file):
    pdb.set_trace()
    image_bytes = image_file.file.read()
    return image_bytes


def upload_blob(bucket_name, image_file, image_hash):
    """Uploads erg_image to google cloud bucket if not already stored"""
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(image_hash)
    if blob.exists():
        print("Duplicate: blob already exists in bucket")
    else:
        pdb.set_trace()
        image_bytes = image_file.file.read()
        # byte_array = bytearray(image_file.file.read())
        # photo_hash = sha256(byte_array).hexdigest()
        # if photo_hash == image_hash:
        #     print("same hashes")
        # else:
        #     print("diff hash")

        blob.upload_from_string(image_bytes, "image/jpeg")
        print(f"{image_hash} with contents {image_file} uploaded to {bucket_name}.")


examine_file()
