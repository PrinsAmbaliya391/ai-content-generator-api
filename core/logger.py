import sys
import time
from jose import jwt
import json
from pathlib import Path
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
import logging
from loguru import logger

# -------------------------
# 1. SETUP PATHS
# -------------------------
BASE_DIR = Path(__file__).resolve().parent.parent
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "activity.log"

# -------------------------
# 2. CONFIGURE LOGGER
# -------------------------
logger.remove()
LOG_FORMAT = (
    "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | {message}"
)


def business_logic_filter(record):
    """
    Filters log records to only include those flagged as 'is_business'.
    This separates system/framework logs from application business logic.
    """
    return record["extra"].get("is_business") is True


# Silence uvicorn logs (Suppress standard INFO: 172.18... logs)
logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
logging.getLogger("uvicorn").setLevel(logging.WARNING)

logger.add(
    sys.stdout,
    format=LOG_FORMAT,
    level="INFO",
    colorize=True,
    enqueue=True,
    filter=business_logic_filter,
)
logger.add(
    str(LOG_FILE),
    format=LOG_FORMAT,
    level="INFO",
    rotation="10 MB",
    retention="7 days",
    colorize=False,
    enqueue=True,
    filter=business_logic_filter,
)


# -------------------------
# 3. MIDDLEWARE
# -------------------------
class BusinessLogicLoggerMiddleware(BaseHTTPMiddleware):
    """
    Starlette middleware for logging HTTP request/response cycles.
    Includes user identity extraction from JWT and performance timing.
    """

    async def dispatch(self, request: Request, call_next):
        start_time = time.perf_counter()
        method = request.method
        path = request.url.path

        # Identify user (simplified for now to avoid body reading issues)
        user_identity = "Anonymous"
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            try:
                token = auth_header.split(" ")[1]
                claims = jwt.get_unverified_claims(token)
                user_identity = claims.get("sub") or "AuthUser"
            except Exception:
                user_identity = "InvalidToken"

        try:
            response = await call_next(request)
            process_time = round((time.perf_counter() - start_time) * 1000, 2)
            status_code = response.status_code

            log_output = (
                f"<cyan>User :</cyan> {user_identity} | "
                f"<magenta>Method :</magenta> {method} - {path} | "
                f"<cyan>Status :</cyan> "
                f"{'<green>' if status_code < 400 else '<red>'}{status_code}{'</green>' if status_code < 400 else '</red>'} | "
                f"<cyan>Time :</cyan> <yellow>{process_time}ms</yellow>"
            )

            if status_code < 400:
                logger.bind(is_business=True).opt(colors=True).info(log_output)
            else:
                logger.bind(is_business=True).opt(colors=True).error(log_output)

            return response

        except Exception as e:
            process_time = round((time.perf_counter() - start_time) * 1000, 2)
            logger.bind(is_business=True).opt(colors=True).error(
                f"<cyan>User :</cyan> {user_identity} | <magenta>Method :</magenta> {method} - {path} | <cyan>Status :</cyan> <red>500</red> | <cyan>Message :</cyan> {str(e)} | <cyan>Time :</cyan> <yellow>{process_time}ms</yellow>"
            )
            raise e
