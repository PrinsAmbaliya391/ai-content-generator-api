from fastapi import APIRouter
from auth.schemas import SignupRequest, LoginRequest, VerifyOTP, ChangePasswordRequest
from auth.services import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/signup")
async def signup(user: SignupRequest):
    return await AuthService.signup(user)


@router.post("/verify-otp")
async def verify(data: VerifyOTP):
    return await AuthService.verify_otp(data)


@router.put("/change-password")
async def change_password(data: ChangePasswordRequest):
    return await AuthService.change_password(data)


@router.post("/login")
async def login(user: LoginRequest):
    return await AuthService.login(user)


@router.post("/verify-login-otp")
async def verify_login_otp(data: VerifyOTP):
    return await AuthService.verify_login_otp(data)
