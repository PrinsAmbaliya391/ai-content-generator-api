"""
Authentication Service Module.

This module handles user authentication flows including signup, login, OTP verification,
password management, and email notifications.
"""

import smtplib
import random
import secrets
import ssl
from email.message import EmailMessage
from fastapi import HTTPException
from datetime import datetime, timedelta, timezone
from html import escape
from core.logger import logger
from core.config import SMTP_EMAIL, SMTP_PASSWORD, SMTP_HOST, SMTP_PORT, SECRET_KEY
from core.database import supabase
import re
import uuid
import asyncio
import hashlib
from jose import jwt
from passlib.context import CryptContext

# Set up password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """
    Hashes a plain-text password using the configured hashing algorithm (bcrypt).

    Args:
        password (str): The plain-text password to hash.

    Returns:
        str: The hashed password.
    """
    return pwd_context.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    """
    Verifies a plain-text password against a hashed password.

    Args:
        password (str): The plain-text password to verify.
        hashed_password (str): The hashed password to compare against.

    Returns:
        bool: True if the password matches the hash, False otherwise.
    """
    return pwd_context.verify(password, hashed_password)


def validate_password_strength(password: str):
    """
    Validates that a password meets complexity requirements.

    Args:
        password (str): The plain-text password to validate.

    Raises:
        HTTPException: If the password fails any complexity checks.
    """
    if len(password) < 8:
        raise HTTPException(
            status_code=400, detail="Password must be at least 8 characters long"
        )

    if not re.search(r"[A-Z]", password):
        raise HTTPException(
            status_code=400,
            detail="Password must contain at least one uppercase letter",
        )

    if not re.search(r"[a-z]", password):
        raise HTTPException(
            status_code=400,
            detail="Password must contain at least one lowercase letter",
        )

    if not re.search(r"[0-9]", password):
        raise HTTPException(
            status_code=400, detail="Password must contain at least one number"
        )

    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        raise HTTPException(
            status_code=400,
            detail="Password must contain at least one special character",
        )


def send_otp(receiver: str) -> str:
    """
    Generates and sends a 6-digit OTP to the specified email.

    Args:
        receiver (str): The destination email address.

    Returns:
        str: The generated OTP if successful, None otherwise.
    """
    otp = str(secrets.randbelow(900000) + 100000)

    msg = EmailMessage()
    msg["Subject"] = "Your OTP Verification Code"
    msg["From"] = SMTP_EMAIL
    msg["To"] = receiver

    html = f"""
<html>
<body style="margin:0;padding:0;background:#eef2f7;font-family:Arial,Helvetica,sans-serif;">

<table width="100%" cellpadding="0" cellspacing="0" style="padding:30px 0;">
<tr>
<td align="center">

<table width="620" cellpadding="0" cellspacing="0" 
style="background:#ffffff;border-radius:12px;overflow:hidden;box-shadow:0 4px 15px rgba(0,0,0,0.05);">

<!-- HEADER -->
<tr>
<td style="background:#4CAF50;padding:25px;text-align:center;color:#ffffff;">

<h1 style="margin:0;font-size:22px;">RejoiceHub</h1>

<p style="margin:5px 0 0 0;font-size:13px;opacity:0.9;">
Secure Account Verification
</p>

</td>
</tr>

<!-- BODY -->
<tr>
<td style="padding:40px;color:#444;font-size:15px;line-height:1.6;">

<p style="margin-top:0;">Hello,</p>

<p>
Thank you for signing up. Use the verification code below to complete
your account verification.
</p>

<!-- OTP BOX -->
<table width="100%" cellpadding="0" cellspacing="0" style="margin:30px 0;">
<tr>
<td align="center">

<div style="
display:inline-block;
background:#f4f7fb;
border:2px dashed #4CAF50;
padding:18px 35px;
font-size:34px;
letter-spacing:8px;
font-weight:bold;
border-radius:10px;
color:#333;
">

{otp}

</div>

</td>
</tr>
</table>

<p style="text-align:center;font-size:14px;color:#777;">
This code will expire in <b>5 minutes</b>.
</p>

<hr style="border:none;border-top:1px solid #eee;margin:30px 0;">

<p style="font-size:13px;color:#888;">
If you didn’t request this email, you can safely ignore it.
</p>

</td>
</tr>

<!-- BUTTON -->
<tr>
<td align="center" style="padding-bottom:35px;">

<a href="https://your-platform-url.com"
style="
background:#4CAF50;
color:#ffffff;
text-decoration:none;
padding:12px 28px;
border-radius:6px;
font-size:14px;
font-weight:bold;
display:inline-block;
">

Visit RejoiceHub

</a>

</td>
</tr>

<!-- FOOTER -->
<tr>
<td style="
background:#f7f9fb;
padding:25px;
text-align:center;
font-size:12px;
color:#999;
">

<p style="margin:0;">
© 2026 RejoiceHub LLP
</p>

<p style="margin:6px 0 0 0;">
Need help?
<a href="https://your-platform-url.com/support"
style="color:#4CAF50;text-decoration:none;">
Contact Support
</a>
</p>

</td>
</tr>

</table>

</td>
</tr>
</table>

</body>
</html>
"""

    msg.add_alternative(html, subtype="html")

    try:
        context = ssl.create_default_context()

        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as smtp:
            smtp.starttls(context=context)
            smtp.login(SMTP_EMAIL, SMTP_PASSWORD)
            smtp.send_message(msg)

        return otp

    except Exception as e:
        logger.bind(is_business=True).error(f"OTP email error: {e}")
        return None


def send_verification_success_email(received: str, username: str) -> bool:
    """
    Sends a welcome email after successful account verification.

    Args:
        received (str): The recipient's email address.
        username (str): The recipient's username for personalization.

    Returns:
        bool: True if the email was sent successfully, False otherwise.
    """
    if not all([SMTP_HOST, SMTP_EMAIL, SMTP_PASSWORD]):
        logger.bind(is_business=True).error("SMTP configuration is missing.")
        return False

    safe_username = escape(username)

    msg = EmailMessage()
    msg["Subject"] = "Welcome to Our Platform! 🎉"
    msg["From"] = SMTP_EMAIL
    msg["To"] = received

    # HTML content for premium look
    html_content = f"""
<html>
<body style="margin:0;padding:0;background:#f4f6f8;font-family:Arial;">

<table width="100%">
<tr>
<td align="center">

<table width="600" style="background:#fff;padding:40px;border-radius:8px">

<tr>
<td align="center">
<h2>Welcome {safe_username} 🎉</h2>
</td>
</tr>

<tr>
<td style="color:#555;font-size:15px">

<p>Your account has been successfully verified.</p>

<p>You can now login and start exploring our platform.</p>

<p style="text-align:center;margin-top:25px">

<a href="https://your-platform-url.com/login"
style="
background:#4CAF50;
color:white;
padding:12px 24px;
text-decoration:none;
border-radius:6px;
font-weight:bold;
">

Login Now

</a>

</p>

</td>
</tr>

<tr>
<td style="border-top:1px solid #eee;padding-top:20px;text-align:center;font-size:12px;color:#999">

© 2026 RejoiceHub LLP

</td>
</tr>

</table>

</td>
</tr>
</table>

</body>
</html>
"""

    msg.add_alternative(html_content, subtype="html")

    try:
        context = ssl.create_default_context()
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls(context=context)
            server.login(SMTP_EMAIL, SMTP_PASSWORD)
            server.send_message(msg)
        return True
    except Exception as e:
        logger.bind(is_business=True).error(f"Welcome email error: {e}")
        return False


def send_verification_success_login_email(received: str, username: str) -> bool:
    """
    Sends a notification email after a successful login.

    Args:
        received (str): The recipient's email address.
        username (str): The user's name.

    Returns:
        bool: True if successful.
    """
    safe_username = escape(username)
    msg = EmailMessage()
    msg["Subject"] = "Login Successful! 🔐"
    msg["From"] = SMTP_EMAIL
    msg["To"] = received

    html_content = f"""
    <html>
    <body style="margin:0;padding:0;background:#f4f6f8;font-family:Arial;">

    <table width="100%">
    <tr>
    <td align="center">

    <table width="600" style="background:#fff;padding:40px;border-radius:8px">

    <tr>
    <td align="center">
    <h2>Login Alert 🔐</h2>
    </td>
    </tr>

    <tr>
    <td style="color:#555;font-size:15px">

    <p>Hello <b>{safe_username}</b>,</p>

    <p>Your account was successfully logged in.</p>

    <p style="color:#d9534f;font-weight:bold">
    If this wasn't you, reset your password immediately.
    </p>

    <p style="text-align:center;margin-top:25px">

    <a href="https://your-platform-url.com/reset-password"
    style="
    background:#d9534f;
    color:white;
    padding:12px 24px;
    text-decoration:none;
    border-radius:6px;
    font-weight:bold;
    ">

    Reset Password

    </a>

    </p>

    </td>
    </tr>

    <tr>
    <td style="border-top:1px solid #eee;padding-top:20px;text-align:center;font-size:12px;color:#999">

    © 2026 RejoiceHub LLP

    </td>
    </tr>

    </table>

    </td>
    </tr>
    </table>

    </body>
    </html>
    """

    msg.add_alternative(html_content, subtype="html")

    try:
        context = ssl.create_default_context()
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as smtp:
            smtp.starttls(context=context)
            smtp.login(SMTP_EMAIL, SMTP_PASSWORD)
            smtp.send_message(msg)
        return True
    except Exception as e:
        logger.bind(is_business=True).error(f"Login notification error: {e}")
        return False


ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 15
REFRESH_TOKEN_EXPIRE_DAYS = 7


def create_access_token(data: dict) -> str:
    """
    Generates a JWT access token.

    Args:
        data (dict): The payload to include in the token.

    Returns:
        str: The encoded JWT.
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(data: dict) -> str:
    """
    Generates a JWT refresh token.

    Args:
        data (dict): The payload to include in the token.

    Returns:
        str: The encoded JWT.
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


class AuthService:
    """
    Service class handling the business logic for authentication.
    """

    @staticmethod
    async def signup(user):
        """
        Handles user registration by validating input and sending an OTP.

        Args:
            user (SignupRequest): The user registration details.
        """
        validate_password_strength(user.password)

        hashed_password = hash_password(user.password)

        existing = await asyncio.to_thread(
            lambda: supabase.table("users")
            .select("*")
            .eq("email", user.email)
            .execute()
        )

        if existing.data:
            raise HTTPException(status_code=400, detail=f"{user.email} already exists")

        otp = await asyncio.to_thread(send_otp, user.email)

        if not otp:
            raise HTTPException(
                status_code=500, detail="Failed to send verification email"
            )

        hashed_otp = hashlib.sha256(otp.encode()).hexdigest()
        new_uuid = str(uuid.uuid4())

        await asyncio.to_thread(
            lambda: supabase.table("users")
            .upsert(
                {
                    "uuid": new_uuid,
                    "username": user.username,
                    "email": user.email,
                    "password": hashed_password,
                    "otp": hashed_otp,
                    "is_verified": False,
                }
            )
            .execute()
        )

        return {"message": f"OTP sent to {user.email}"}

    @staticmethod
    async def verify_otp(data):
        """
        Verifies the OTP provided during signup and activates the user account.

        Args:
            data (VerifyOTP): The email and OTP to verify.
        """
        response = await asyncio.to_thread(
            lambda: supabase.table("users")
            .select("*")
            .eq("email", data.email)
            .execute()
        )

        if not response.data:
            raise HTTPException(status_code=404, detail="User not found")

        hashed_input_otp = hashlib.sha256(data.otp.encode()).hexdigest()

        if response.data[0]["otp"] != hashed_input_otp:
            raise HTTPException(status_code=400, detail="Invalid OTP")

        await asyncio.to_thread(
            lambda: supabase.table("users")
            .update({"is_verified": True, "otp": None})
            .eq("email", data.email)
            .execute()
        )

        username = response.data[0]["username"]
        await asyncio.to_thread(send_verification_success_email, data.email, username)

        return {"message": "Verification successful"}

    @staticmethod
    async def login(user):
        """
        Authenticates a user and sends a login OTP if credentials are valid.

        Args:
            user (LoginRequest): Login credentials.
        """
        response = await asyncio.to_thread(
            lambda: supabase.table("users")
            .select("*")
            .eq("email", user.email)
            .execute()
        )

        if not response.data:
            raise HTTPException(status_code=401, detail="Invalid email or password")

        db_user = response.data[0]

        if not verify_password(user.password, db_user["password"]):
            raise HTTPException(status_code=401, detail="Invalid email or password")

        if not db_user["is_verified"]:
            raise HTTPException(
                status_code=403, detail="Please verify your email first"
            )

        otp = await asyncio.to_thread(send_otp, user.email)

        if not otp:
            raise HTTPException(status_code=500, detail="Failed to send login OTP")

        hashed_otp = hashlib.sha256(otp.encode()).hexdigest()

        await asyncio.to_thread(
            lambda: supabase.table("users")
            .update({"otp": hashed_otp})
            .eq("email", user.email)
            .execute()
        )

        return {"message": f"Login OTP sent to {user.email}"}

    @staticmethod
    async def verify_login_otp(data):
        """
        Verifies the login OTP and returns JWT tokens.

        Args:
            data (VerifyOTP): Login verification details.
        """
        response = await asyncio.to_thread(
            lambda: supabase.table("users")
            .select("uuid, otp, username, updated_at, email")
            .eq("email", data.email)
            .execute()
        )

        if not response.data:
            raise HTTPException(status_code=404, detail="User not found")

        hashed_input_otp = hashlib.sha256(data.otp.encode()).hexdigest()

        if response.data[0]["otp"] != hashed_input_otp:
            raise HTTPException(status_code=400, detail="Invalid OTP")

        otp_time = datetime.fromisoformat(
            response.data[0]["updated_at"].replace("Z", "+00:00")
        )

        if datetime.now(timezone.utc) > otp_time + timedelta(minutes=5):
            raise HTTPException(status_code=400, detail="OTP expired")

        user_uuid = str(response.data[0]["uuid"])
        access_token = create_access_token({"sub": user_uuid})
        refresh_token = create_refresh_token({"sub": user_uuid})

        username = response.data[0]["username"]
        await asyncio.to_thread(
            send_verification_success_login_email, data.email, username
        )

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "user": {"username": username, "email": data.email},
        }

    @staticmethod
    async def change_password(data):
        """
        Updates the user's password after verifying the old one.

        Args:
            data (ChangePasswordRequest): Password change details.
        """
        # Fetch user
        response = await asyncio.to_thread(
            lambda: supabase.table("users")
            .select("*")
            .eq("email", data.email)
            .execute()
        )

        if not response.data:
            raise HTTPException(status_code=404, detail="User not found")

        db_user = response.data[0]

        # Verify old password

        if not verify_password(data.old_password, db_user["password"]):
            raise HTTPException(status_code=401, detail="Invalid old password")

        # Validate and hash new password
        validate_password_strength(data.new_password)
        hashed_new_password = hash_password(data.new_password)

        # Update in database
        await asyncio.to_thread(
            lambda: supabase.table("users")
            .update({"password": hashed_new_password})
            .eq("email", data.email)
            .execute()
        )

        logger.bind(is_business=True).info(
            f"Password changed successfully for user: {data.email}"
        )
        return {"message": "Password changed successfully"}


auth_service = AuthService()
