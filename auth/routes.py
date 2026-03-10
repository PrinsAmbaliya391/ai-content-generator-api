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
    Verifies the OTP sent during signup.
    This endpoint checks if the provided OTP matches the one stored in the database for the user.
    """
    return await AuthService.verify_otp(data)


@router.put("/change-password")
async def change_password(data: ChangePasswordRequest):
    """
    Changes the password for an authenticated user.
    This endpoint verifies the old password and updates it with the new provided password.
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
    Finalizes the login process by verifying the login OTP.
    This endpoint returns the JWT access and refresh tokens upon successful verification.
    """
    return await AuthService.verify_login_otp(data)
