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
    colorize=True,
    enqueue=True,
    filter=business_logic_filter,
)


# -------------------------
# 3. MIDDLEWARE
# -------------------------
class BusinessLogicLoggerMiddleware(BaseHTTPMiddleware):

    async def dispatch(self, request: Request, call_next):
        start_time = time.perf_counter()

        # ---------------------------------------------------------
        # UPDATE 1: Try to get User Identity from Request Body if no token
        # (This prevents /auth/login from showing as "Anonymous")
        # ---------------------------------------------------------
        user_identity = "Anonymous"
        auth_header = request.headers.get("Authorization")

        if auth_header and auth_header.startswith("Bearer "):
            try:
                token = auth_header.split(" ")[1]
                claims = jwt.get_unverified_claims(token)
                user_identity = claims.get("sub") or "AuthUser"
            except Exception:
                user_identity = "InvalidToken"
        else:
            # If no token, check if it's a login attempt and use email as temporary ID
            try:
                body_bytes = await request.body()

                # We must re-wrap the request body so the actual route can read it later
                async def receive():
                    return {"type": "http.request", "body": body_bytes}

                request._receive = receive

                if body_bytes:
                    req_json = json.loads(body_bytes.decode())
                    user_identity = req_json.get("email") or "Anonymous"
            except:
                pass

        method = request.method
        path = request.url.path

        try:
            response = await call_next(request)
            process_time = round((time.perf_counter() - start_time) * 1000, 2)
            status_code = response.status_code

            body = b""
            async for chunk in response.body_iterator:
                body += chunk

            new_response = Response(
                content=body,
                status_code=status_code,
                headers=dict(response.headers),
                media_type=response.media_type,
            )

            # ---------------------------------------------------------
            # UPDATE 2: Extract Message AND UUID from the Response
            # (Ensures 'Message' is present in success logs)
            # ---------------------------------------------------------
            message = "Success"
            try:
                resp_json = json.loads(body.decode())
                # Capture custom message or detail from the API
                message = (
                    resp_json.get("message") or resp_json.get("detail") or "Success"
                )

                # If the login was successful, the access_token contains the UUID
                if "access_token" in resp_json:
                    token_claims = jwt.get_unverified_claims(resp_json["access_token"])
                    user_identity = token_claims.get("sub") or user_identity
            except Exception:
                message = body.decode()[:100] if body else "Success"

            # ---------------------------------------------------------
            # UPDATE 3: Use the exact log format you requested
            # ---------------------------------------------------------
            log_output = (
                f"<cyan>User :</cyan> {user_identity} | "
                f"<magenta>Method :</magenta> {method} - {path} | "
                f"<cyan>Status :</cyan> "
                f"{'<green>' if status_code < 400 else '<red>'}{status_code}{'</green>' if status_code < 400 else '</red>'} | "
                f"<cyan>Message :</cyan> {message} | "
                f"<cyan>Time :</cyan> <yellow>{process_time}ms</yellow>"
            )

            if status_code < 400:
                logger.bind(is_business=True).opt(colors=True).info(log_output)
            else:
                logger.bind(is_business=True).opt(colors=True).error(log_output)

            return new_response

        except Exception as e:
            process_time = round((time.perf_counter() - start_time) * 1000, 2)
            logger.bind(is_business=True).opt(colors=True).error(
                f"<cyan>User :</cyan> {user_identity} | <magenta>Method :</magenta> {method} - {path} | <cyan>Status :</cyan> <red>500</red> | <cyan>Message :</cyan> {str(e)} | <cyan>Time :</cyan> <yellow>{process_time}ms</yellow>"
            )
            raise e
