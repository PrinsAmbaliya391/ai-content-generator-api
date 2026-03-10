"""
Main Application Entry Point.
This module initializes the FastAPI application and aggregates
all individual routers for authentication, content generation, and chat.
"""

from fastapi import FastAPI
from core.logger import BusinessLogicLoggerMiddleware
from auth.routes import router as auth_router
from content.routes import router as content_router
from chat.routes import router as chat_router

"""The main FastAPI application instance."""
app = FastAPI(title="AI Content Generator API")

app.add_middleware(BusinessLogicLoggerMiddleware)

"""Register authentication routes for user management."""
app.include_router(auth_router)

"""Register content generation routes for AI tasks."""
app.include_router(content_router)

"""Register chat routes for real-time interaction."""
app.include_router(chat_router)
