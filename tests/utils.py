from src import utils as u

def generate_token(uid="fake-auth-uid"):
    token = u.create_encrypted_token(uid)
    return "Bearer " + str(token, "utf-8")
