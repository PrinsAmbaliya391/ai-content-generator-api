"""
Authentication Service Module.

This module handles user authentication flows including signup, login, OTP verification,
password management, and email notifications.
"""

import smtplib
import random
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
from passlib.context import CryptContext

# Set up password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


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
    otp = str(random.randint(100000, 999999))

    msg = EmailMessage()
    msg.set_content(f"Your OTP code is: {otp}")
    msg["Subject"] = "Your Verification Code"
    msg["From"] = SMTP_EMAIL
    msg["To"] = receiver

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as smtp:
            smtp.starttls()
            smtp.login(SMTP_EMAIL, SMTP_PASSWORD)
            smtp.send_message(msg)
        return otp
    except Exception as e:
        logger.bind(is_business=True).error(f"Failed to send OTP email: {e}")
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

    # Plain text fallback
    msg.set_content(
        f"""Hi {safe_username},

Welcome to our platform!

Your account has been successfully created.
You can now log in and start exploring.

Best regards,
RejoiceHub LLP
Support Team
"""
    )

    # HTML content for premium look
    html_content = f"""
    <html>
<body style="margin:0;padding:0;font-family:Arial,sans-serif;background:#f4f6f8;">
  <table width="100%" cellpadding="0" cellspacing="0" style="padding:20px 0;">
    <tr>
      <td align="center">
        <table width="600" cellpadding="0" cellspacing="0"
               style="background:#ffffff;border-radius:8px;padding:30px;">

          <tr>
            <td align="center">
              <h2 style="color:#333;">Welcome, {safe_username}! 🎉</h2>
            </td>
          </tr>

          <tr>
            <td style="color:#555;font-size:15px;line-height:1.6;">
              <p>Your account has been successfully created.</p>
              <p>You can now log in and start exploring our platform.</p>

              <p style="margin:25px 0;">
                <a href="https://your-platform-url.com/login"
                   style="background:#4CAF50;color:white;
                          padding:12px 20px;text-decoration:none;
                          border-radius:4px;font-weight:bold;">
                  Log In Now
                </a>
              </p>

              <p style="font-size:13px;color:#777;">
                If you didn’t create this account, please ignore this email.
              </p>
            </td>
          </tr>

          <tr>
            <td style="border-top:1px solid #eee;padding-top:20px;
                       font-size:12px;color:#999;text-align:center;">
              © 2026 RejoiceHub LLP<br/>
              <a href="https://your-platform-url.com/help"
                 style="color:#4CAF50;text-decoration:none;">
                 Help Center
              </a>
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

    # Plain-text fallback
    msg.set_content(
        f"""Hi {safe_username},

You’ve successfully logged in.

If this wasn’t you, reset your password immediately.

Best regards,
RejoiceHub LLP
Support Team
"""
    )

    # HTML version
    msg.add_alternative(
        f"""\
<html>
<body style="margin:0;padding:0;font-family:Arial,sans-serif;background:#f4f6f8;">
  <table width="100%" cellpadding="0" cellspacing="0" style="padding:20px 0;">
    <tr>
      <td align="center">
        <table width="600" cellpadding="0" cellspacing="0"
               style="background:#ffffff;border-radius:8px;padding:30px;">

          <tr>
            <td align="center">
              <h2 style="color:#333;">Login Alert 🔐</h2>
            </td>
          </tr>

          <tr>
            <td style="color:#555;font-size:15px;line-height:1.6;">
              <p>Hi <strong>{safe_username}</strong>,</p>

              <p>You’ve successfully logged into your account.</p>

              <p style="color:#d9534f;font-weight:bold;">
                If this wasn’t you, please reset your password immediately.
              </p>

              <p style="margin:25px 0;">
                <a href="http://127.0.0.1:8000/auth/change-password"
                   style="background:#d9534f;color:white;
                          padding:12px 20px;text-decoration:none;
                          border-radius:4px;font-weight:bold;">
                  Reset Password
                </a>
              </p>
            </td>
          </tr>

          <tr>
            <td style="border-top:1px solid #eee;padding-top:20px;
                       font-size:12px;color:#999;text-align:center;">
              © 2026 RejoiceHub LLP<br/>
              <a href="https://your-platform-url.com/help"
                 style="color:#4CAF50;text-decoration:none;">
                 Help Center
              </a>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>
</body>
</html>
""",
        subtype="html",
    )

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
ACCESS_TOKEN_EXPIRE_MINUTES = 6000
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

        hashed_password = pwd_context.hash(user.password)
        new_uuid = str(uuid.uuid4())

        await asyncio.to_thread(
            lambda: supabase.table("users")
            .upsert(
                {
                    "uuid": new_uuid,
                    "username": user.username,
                    "email": user.email,
                    "password": hashed_password,
                    "otp": otp,
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

        if response.data[0]["otp"] != data.otp:
            raise HTTPException(status_code=400, detail="Invalid OTP")

        await asyncio.to_thread(
            lambda: supabase.table("users")
            .update({"is_verified": True})
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

        if not pwd_context.verify(user.password, db_user["password"]):
            raise HTTPException(status_code=401, detail="Invalid email or password")

        if not db_user["is_verified"]:
            raise HTTPException(
                status_code=403, detail="Please verify your email first"
            )

        otp = await asyncio.to_thread(send_otp, user.email)

        if not otp:
            raise HTTPException(status_code=500, detail="Failed to send login OTP")

        await asyncio.to_thread(
            lambda: supabase.table("users")
            .update({"otp": otp})
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

        if response.data[0]["otp"] != data.otp:
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
        if not pwd_context.verify(data.old_password, db_user["password"]):
            raise HTTPException(status_code=401, detail="Invalid old password")

        # Validate and hash new password
        validate_password_strength(data.new_password)
        hashed_new_password = pwd_context.hash(data.new_password)

        # Update in database
        await asyncio.to_thread(
            lambda: supabase.table("users")
            .update({"password": hashed_new_password})
            .eq("email", data.email)
            .execute()
        )

        logger.bind(is_business=True).info(f"Password changed successfully for user: {data.email}")
        return {"message": "Password changed successfully"}


auth_service = AuthService()
