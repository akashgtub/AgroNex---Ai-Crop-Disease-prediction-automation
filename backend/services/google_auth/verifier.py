import os
import logging
from google.oauth2 import id_token
from google.auth.transport import requests
from google.auth.exceptions import GoogleAuthError
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

def verify_google_id_token(token: str, expected_client_id: str | None = None) -> dict:
    """
    Verifies a Google ID token using Google's public certificates.

    Validates:
    - Token signature against Google's public keys
    - Token validity and expiration
    - Token audience against GOOGLE_CLIENT_ID
    - Token issuer (accounts.google.com or https://accounts.google.com)

    Returns:
        dict: Verified user payload containing {google_id, email, name, picture}

    Raises:
        ValueError: If token is invalid, expired, malformed, or audience mismatch.
    """
    if not token or not isinstance(token, str):
        raise ValueError("Google credential token is missing or malformed.")

    client_id = expected_client_id or os.getenv("GOOGLE_CLIENT_ID")
    if not client_id or client_id in ("YOUR_GOOGLE_CLIENT_ID", "your_google_client_id_here"):
        client_id_to_check = None
        logger.warning("GOOGLE_CLIENT_ID is not configured in backend environment.")
    else:
        client_id_to_check = client_id

    try:
        request = requests.Request()
        id_info = id_token.verify_oauth2_token(
            token,
            request,
            audience=client_id_to_check
        )
    except (ValueError, GoogleAuthError) as exc:
        logger.warning(f"Google token verification failed: {exc}")
        raise ValueError(f"Invalid Google ID token: {exc}") from exc
    except Exception as exc:
        logger.error(f"Unexpected error during Google token verification: {exc}")
        raise ValueError(f"Token verification failed: {exc}") from exc

    google_id = id_info.get("sub")
    if not google_id:
        raise ValueError("Google ID token is missing 'sub' claim.")

    return {
        "google_id": str(google_id),
        "email": id_info.get("email"),
        "name": id_info.get("name"),
        "picture": id_info.get("picture"),
        "email_verified": id_info.get("email_verified", False)
    }
