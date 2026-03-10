<<<<<<< HEAD
"""
Authentication Schemas Module.

This module defines the Pydantic models for authentication-related
requests and responses.
"""

=======
>>>>>>> bb1d64e96c32bb861b35557a0b54ee61969be875
from pydantic import BaseModel


class SignupRequest(BaseModel):
<<<<<<< HEAD
    """
    Schema for user registration requests.
    """

=======
>>>>>>> bb1d64e96c32bb861b35557a0b54ee61969be875
    username: str
    email: str
    password: str


class LoginRequest(BaseModel):
<<<<<<< HEAD
    """
    Schema for user login requests.
    """

=======
>>>>>>> bb1d64e96c32bb861b35557a0b54ee61969be875
    email: str
    password: str


class RefreshTokenRequest(BaseModel):
<<<<<<< HEAD
    """
    Schema for JWT refresh token requests.
    """

=======
>>>>>>> bb1d64e96c32bb861b35557a0b54ee61969be875
    refresh_token: str


class VerifyOTP(BaseModel):
<<<<<<< HEAD
    """
    Schema for OTP verification requests (signup and login).
    """

=======
>>>>>>> bb1d64e96c32bb861b35557a0b54ee61969be875
    email: str
    otp: str


class ChangePasswordRequest(BaseModel):
<<<<<<< HEAD
    """
    Schema for password change requests.
    """

=======
>>>>>>> bb1d64e96c32bb861b35557a0b54ee61969be875
    email: str
    old_password: str
    new_password: str
