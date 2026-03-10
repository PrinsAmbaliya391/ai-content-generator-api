"""
Authentication Schemas Module.

This module defines the Pydantic models for authentication-related
requests and responses.
"""

from pydantic import BaseModel


class SignupRequest(BaseModel):
    """
    Schema for user registration requests.
    """

    username: str
    email: str
    password: str


class LoginRequest(BaseModel):
    """
    Schema for user login requests.
    """

    email: str
    password: str


class RefreshTokenRequest(BaseModel):
    """
    Schema for JWT refresh token requests.
    """

    refresh_token: str


class VerifyOTP(BaseModel):
    """
    Schema for OTP verification requests (signup and login).
    """

    email: str
    otp: str


class ChangePasswordRequest(BaseModel):
    """
    Schema for password change requests.
    """

    email: str
    old_password: str
    new_password: str
