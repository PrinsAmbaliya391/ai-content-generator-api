"""
Main Application Entry Point.
This module initializes the FastAPI application and aggregates
all individual routers for authentication, content generation, and chat.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from core.logger import BusinessLogicLoggerMiddleware
from auth.routes import router as auth_router
from content.routes import router as content_router
from chat.routes import router as chat_router

app = FastAPI(title="AI Content Generator API")

# ── CORS ──────────────────────────────────────────────────────────────────────
# Allow the frontend (Vite dev on 8080, Docker on 3000) to call the backend.
# Change allow_origins to your production domain before deploying publicly.
app.add_middleware(
    CORSMiddleware,
    # Replace with your exact frontend URL(s)
    allow_origins=[
        "*"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── MIDDLEWARE ────────────────────────────────────────────────────────────────
# Add custom middleware for business logic logging
app.add_middleware(BusinessLogicLoggerMiddleware)

# ── ROUTERS ───────────────────────────────────────────────────────────────────
# Registering application routers
app.include_router(auth_router)
app.include_router(content_router)
app.include_router(chat_router)

# ── STARTUP ───────────────────────────────────────────────────────────────────
# Add any startup events if necessary (e.g., db connection verification)