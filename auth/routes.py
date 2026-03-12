"""
Authentication Routes Module.

This module defines the API endpoints for user registration, login,
OTP verification, and password management.
"""

from fastapi import APIRouter
from auth.schemas import SignupRequest, LoginRequest, VerifyOTP, ChangePasswordRequest
from auth.services import auth_service as AuthService

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/signup")
async def signup(user: SignupRequest):
    """
    Registers a new user.

    Args:
        user (SignupRequest): The user registration data.

    Returns:
        dict: A message indicating successful registration.
    """
    return await AuthService.signup(user)


@router.post("/verify-otp")
async def verify(data: VerifyOTP):
    """
    Verifies the email OTP provided by the user during signup.

    Args:
        data (VerifyOTP): Object containing email and the 6-digit OTP.

    Returns:
        dict: A success message if verification passes.
    """
    return await AuthService.verify_otp(data)


@router.put("/change-password")
async def change_password(data: ChangePasswordRequest):
    """
    Changes the password for an existing user.

    Args:
        data (ChangePasswordRequest): Object containing email, old password, and new password.

    Returns:
        dict: A success message if the password was updated.
    """
    return await AuthService.change_password(data)


@router.post("/login")
async def login(user: LoginRequest):
    """
    Initiates the login process for a user.
    This endpoint verifies credentials and, if valid, sends a login OTP to the user's email.
    """
    return await AuthService.login(user)


@router.post("/verify-login-otp")
async def verify_login_otp(data: VerifyOTP):
    """
    Verifies the 2FA login OTP and issues authentication tokens.

    Args:
        data (VerifyOTP): Object containing email and the 6-digit login OTP.

    Returns:
        dict: Access and refresh tokens, along with user details.
    """
    return await AuthService.verify_login_otp(data)
