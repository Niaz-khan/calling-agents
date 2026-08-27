from fastapi import FastAPI, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session
from .database import get_db

from app.config import settings
from app.api.routes.agents import router as agents_router
from app.api.routes.auth import router as auth_router
from app.api.routes.calls import router as calls_router
from app.api.routes.chat import router as chat_router
from app.api.routes.voice import router as voice_router

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version
)

app.include_router(agents_router)
app.include_router(auth_router)
app.include_router(chat_router)
app.include_router(calls_router)
app.include_router(voice_router)

@app.get("/")
def root():
    return{
        "message": "AI Calling Agent",
        "version": f"{settings.app_version}"
    }


@app.get("/health")
def health():
    return{
        "status": "ok"
    }

@app.get("/db-health")
def db_health(db: Session = Depends(get_db)):
    result = db.execute(text("Select 1"))
    value = result.scalar()

    return {
        "message": "Database connected",
        "test": value
    }