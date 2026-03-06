from fastapi import FastAPI
from auth.routes import router as auth_router
from content.routes import router as content_router
from chat.routes import router as chat_router


app = FastAPI(title="AI Content Generator API")

app.include_router(auth_router)
app.include_router(content_router)
app.include_router(chat_router)
