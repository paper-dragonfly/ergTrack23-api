from pydantic import BaseModel


# Response
class Response(BaseModel):
    status_code: int = 200
    error_message: str = None
    body: dict = None


class CustomError(Exception):
    pass
