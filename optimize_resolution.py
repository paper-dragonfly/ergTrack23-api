import os
import time
from PIL import Image
from fastapi import UploadFile
import requests
import io
from tests.utils import generate_token

# Directory containing images
IMAGE_DIR = 'erg_images'

# API Endpoint
API_ENDPOINT = 'http://localhost:8000/ergimage'

# Create token 
AUTH_UID = "fake-auth-uid"
AUTH_TOKEN = generate_token(AUTH_UID)

# Images that cannot be processed
CANNOT_OCR = []

# Function to post image and record response time
def post_image(image_path, image_size, unprocessable_images = CANNOT_OCR):
    # Convert image to UploadFile instance
    with open(image_path, 'rb') as image_file:
        image_data = image_file.read()
    image_stream = io.BytesIO(image_data)
    image_stream.seek(0)
    upload_file = UploadFile(filename=image_path, file=image_stream)

    # POST the image to the endpoint
    files = {'file': (upload_file.filename, upload_file.file, 'image/jpeg')}
    start_time = time.time()
    response = requests.post(API_ENDPOINT, files=files)
    response_time = time.time() - start_time

    # Check successful OCR 
    if response.status_code != 200:
        name = image_path.split('/')[-1]
        unprocessable_images.append(name) 
        return False 
    
    # Check if image size matches expected size
    image_size_matches = response.json().get('image_size', None) == image_size

    return response.json(), response_time, response.json().get('image_size', None), image_size_matches

def compare_ocr_quality_at_different_resolutions(IMAGE_DIR): 
    # Cycle through images in the directory
    for filename in os.listdir(IMAGE_DIR):
        if not filename.lower().endswith(('.png', '.jpg', '.jpeg', '.tiff', '.bmp', '.gif')):
            continue

        image_path = os.path.join(IMAGE_DIR, filename)
        original_image = Image.open(image_path)
        original_size = original_image.size

        image = original_image
        image_size_percentage = 100

        response_data_100 = None
        while image_size_percentage >= 15:
            # Step 2-4: Post image and record response time
            response_data, response_time, _ = post_image(image_path, image.size)

            # Save the response for 100% resolution for future comparison
            if image_size_percentage == 100:
                response_data_100 = response_data

            # Step 5: Halve the size of the image
            new_width = int(image.size[0] * 0.5)
            new_height = int(image.size[1] * 0.5)
            image = image.resize((new_width, new_height), Image.ANTIALIAS)

            # Save the resized image temporarily to post it again
            temp_image_path = 'temp_' + filename
            image.save(temp_image_path)

            # Step 6: Repeat steps 2-4 and compare responses
            response_data_half, response_time_half, image_size_matches = post_image(temp_image_path, image.size)

            # Compare the responses
            is_identical_response = response_data_100 == response_data_half

            print(f"Image: {filename} | Original Size: {original_size} | New Size: {image.size} | "
                f"Response Time (full size): {response_time:.4f}s | "
                f"Response Time (half size): {response_time_half:.4f}s | "
                f"Responses Identical: {is_identical_response}")

            # Step 7: Repeat step 4-5 until the image quality is <15% of original resolution
            image_size_percentage = (image.size[0] / original_size[0]) * 100

            # Clean up the temporary file
            os.remove(temp_image_path)

        original_image.close()
