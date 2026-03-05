from pydantic import BaseModel


class SignupRequest(BaseModel):
    username: str
    email: str
    password: str


class LoginRequest(BaseModel):
    email: str
    password: str


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class VerifyOTP(BaseModel):
    email: str
    otp: str


class ChangePasswordRequest(BaseModel):
    email: str
    old_password: str
    new_password: str
