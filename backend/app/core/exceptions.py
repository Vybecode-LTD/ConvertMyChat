"""Custom HTTP exceptions."""

from fastapi import HTTPException, status


class ExtractionError(HTTPException):
    def __init__(self, detail: str = "Failed to extract conversation"):
        super().__init__(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=detail)

class InvalidShareLink(HTTPException):
    def __init__(self, detail: str = "Invalid Gemini share link format"):
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)

class ScraperBusy(HTTPException):
    def __init__(self):
        super().__init__(status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                         detail="Server busy. Try again shortly.")

class ShareLinkExpired(HTTPException):
    def __init__(self):
        super().__init__(status_code=status.HTTP_404_NOT_FOUND,
                         detail="This shared conversation no longer exists.")

class Unauthorized(HTTPException):
    def __init__(self, detail: str = "Not authenticated"):
        super().__init__(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail,
                         headers={"WWW-Authenticate": "Bearer"})

class Forbidden(HTTPException):
    def __init__(self, detail: str = "Admin access required"):
        super().__init__(status_code=status.HTTP_403_FORBIDDEN, detail=detail)
