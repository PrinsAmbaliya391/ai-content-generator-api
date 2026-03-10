<<<<<<< HEAD
"""
Security Dependency Module.

This module provides FastAPI dependencies for JWT token verification
and user authentication.
"""

=======
>>>>>>> bb1d64e96c32bb861b35557a0b54ee61969be875
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from core.config import SECRET_KEY, ALGORITHM
<<<<<<< HEAD
from core.logger import logger
=======
>>>>>>> bb1d64e96c32bb861b35557a0b54ee61969be875

security = HTTPBearer()


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
<<<<<<< HEAD
    """
    FastAPI dependency to validate JWT access tokens.

    Args:
        credentials (HTTPAuthorizationCredentials): The bearer token from the header.

    Returns:
        str: The user UUID from the token payload.

    Raises:
        HTTPException: If the token is invalid, expired, or of wrong type.
    """
=======
>>>>>>> bb1d64e96c32bb861b35557a0b54ee61969be875
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

        if payload.get("type") != "access":
<<<<<<< HEAD
            logger.warning("Invalid token type provided in request.")
=======
>>>>>>> bb1d64e96c32bb861b35557a0b54ee61969be875
            raise HTTPException(status_code=401, detail="Invalid token type")

        user_uuid = payload.get("sub")
        if user_uuid is None:
<<<<<<< HEAD
            logger.error("Token payload missing subject (user UUID).")
=======
>>>>>>> bb1d64e96c32bb861b35557a0b54ee61969be875
            raise HTTPException(status_code=401, detail="Invalid token payload")

        return user_uuid

<<<<<<< HEAD
    except JWTError as e:
        logger.warning(f"JWT verification failed: {e}")
=======
    except JWTError:
>>>>>>> bb1d64e96c32bb861b35557a0b54ee61969be875
        raise HTTPException(status_code=401, detail="Token expired or invalid")
