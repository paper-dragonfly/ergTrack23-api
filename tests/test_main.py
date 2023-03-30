from fastapi.testclient import TestClient
import pytest  
import io

from src.schemas import PostWorkoutSchema
from src.main import app

client = TestClient(app)

# def test_create_workout():
#     # Define test data
#     formData = PostWorkoutSchema(
#         entryMethod='manual',
#         workoutType='singleDistance', 
#         workoutLength='2000m', 
#         subWorkouts='4'
#         ).dict() 

#     # Make a POST request to the /workout endpoint with the test data
#     response = client.post("/workout", json=formData)

#     # Check that the response status code is 200 OK
#     assert response.status_code == 200

#     # Check that the response body contains the expected message
#     assert response.json() == "formData received"

def test_create_workout():
    # Create a mock image file
    image_data = b"1234567890"
    image_file = io.BytesIO(image_data)
    image_file.name = "test.jpg"

    # Send a POST request to the endpoint with form data and an image
    response = client.post("/person",
                           data={"name": "John Doe", "age": 30},
                           files={"image": ("test.jpg", image_file, "image/jpeg")})

    # Assert that the response has a status code of 200 OK
    assert response.status_code == 200

    # Assert that the response body contains the correct data
    response_data = response.json()
    assert response_data["name"] == "John Doe"
    assert response_data["age"] == 30
    assert response_data["image"] == image_data