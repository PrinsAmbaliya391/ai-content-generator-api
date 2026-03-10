<<<<<<< HEAD
"""
Authentication Routes Module.

This module defines the API endpoints for user registration, login,
OTP verification, and password management.
"""

=======
>>>>>>> bb1d64e96c32bb861b35557a0b54ee61969be875
from fastapi import APIRouter
from auth.schemas import SignupRequest, LoginRequest, VerifyOTP, ChangePasswordRequest
from auth.services import auth_service as AuthService

<<<<<<< HEAD
=======

>>>>>>> bb1d64e96c32bb861b35557a0b54ee61969be875
router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/signup")
async def signup(user: SignupRequest):
<<<<<<< HEAD
    """
    Registers a new user.

    Args:
        user (SignupRequest): The user registration data.

    Returns:
        dict: A message indicating successful registration.
    """
=======
>>>>>>> bb1d64e96c32bb861b35557a0b54ee61969be875
    return await AuthService.signup(user)


@router.post("/verify-otp")
async def verify(data: VerifyOTP):
<<<<<<< HEAD
    """
    Verifies the OTP sent during signup.
    This endpoint checks if the provided OTP matches the one stored in the database for the user.
    """
=======
>>>>>>> bb1d64e96c32bb861b35557a0b54ee61969be875
    return await AuthService.verify_otp(data)


@router.put("/change-password")
async def change_password(data: ChangePasswordRequest):
<<<<<<< HEAD
    """
    Changes the password for an authenticated user.
    This endpoint verifies the old password and updates it with the new provided password.
    """
=======
>>>>>>> bb1d64e96c32bb861b35557a0b54ee61969be875
    return await AuthService.change_password(data)


@router.post("/login")
async def login(user: LoginRequest):
<<<<<<< HEAD
    """
    Initiates the login process for a user.
    This endpoint verifies credentials and, if valid, sends a login OTP to the user's email.
    """
=======
>>>>>>> bb1d64e96c32bb861b35557a0b54ee61969be875
    return await AuthService.login(user)


@router.post("/verify-login-otp")
async def verify_login_otp(data: VerifyOTP):
<<<<<<< HEAD
    """
    Finalizes the login process by verifying the login OTP.
    This endpoint returns the JWT access and refresh tokens upon successful verification.
    """
=======
>>>>>>> bb1d64e96c32bb861b35557a0b54ee61969be875
    return await AuthService.verify_login_otp(data)
