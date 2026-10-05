import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from services.google_auth import verify_google_id_token

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/google-auth", tags=["Google Authentication"])

class GoogleLoginRequest(BaseModel):
    credential: str

class GoogleUserData(BaseModel):
    google_id: str
    email: Optional[str] = None
    name: Optional[str] = None
    picture: Optional[str] = None

class GoogleLoginResponse(BaseModel):
    success: bool
    user: GoogleUserData

@router.post("/login", response_model=GoogleLoginResponse)
def google_login(payload: GoogleLoginRequest):
    """
    Receives and securely verifies a Google ID token from the frontend.
    Returns verified user profile information without trusting unverified frontend data.
    """
    if not payload.credential or not payload.credential.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google credential token is required."
        )

    try:
        verified_user = verify_google_id_token(payload.credential.strip())
        return GoogleLoginResponse(
            success=True,
            user=GoogleUserData(
                google_id=verified_user["google_id"],
                email=verified_user.get("email"),
                name=verified_user.get("name"),
                picture=verified_user.get("picture"),
            )
        )
    except ValueError as exc:
        logger.warning(f"Google login authentication failed: {exc}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Google credentials."
        )
    except Exception as exc:
        logger.error(f"Internal error processing Google login: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while processing Google login."
        )
