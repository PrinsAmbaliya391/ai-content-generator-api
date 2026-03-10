<<<<<<< HEAD
"""
Main Application Entry Point.
This module initializes the FastAPI application and aggregates
all individual routers for authentication, content generation, and chat.
"""

from fastapi import FastAPI
from core.logger import BusinessLogicLoggerMiddleware
=======
from fastapi import FastAPI
>>>>>>> bb1d64e96c32bb861b35557a0b54ee61969be875
from auth.routes import router as auth_router
from content.routes import router as content_router
from chat.routes import router as chat_router

<<<<<<< HEAD
"""The main FastAPI application instance."""
app = FastAPI(title="AI Content Generator API")

app.add_middleware(BusinessLogicLoggerMiddleware)

"""Register authentication routes for user management."""
app.include_router(auth_router)

"""Register content generation routes for AI tasks."""
app.include_router(content_router)

"""Register chat routes for real-time interaction."""
=======

app = FastAPI(title="AI Content Generator API")

app.include_router(auth_router)
app.include_router(content_router)
>>>>>>> bb1d64e96c32bb861b35557a0b54ee61969be875
app.include_router(chat_router)
