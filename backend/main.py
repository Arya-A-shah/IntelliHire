import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from beanie import init_beanie
from pymongo import AsyncMongoClient
import os
import socketio
from models import User, Job, Application, Interview
from config import settings
from routers import auth, users, jobs, applications, interviews

# --- Socket.IO ---
from core.socket import sio
import controllers.interview as interview  # AI namespace handlers
# ← ADD THIS! PROC namespace handlers
import controllers.proctoring as proctoring

# --- Lifespan for database connection ---


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    # FIX: Beanie 2.0 is built on PyMongo's own async client, not Motor
    # (Motor is being retired by MongoDB). Mixing them can break queries.
    client = AsyncMongoClient(settings.MONGODB_URI)
    await init_beanie(
        database=client[settings.MONGO_DB_NAME],
        document_models=[User, Job, Application, Interview]
    )
    print("MongoDB connected")
    print("Socket.IO namespaces registered: /ai, /proc")

    yield
    # Shutdown
    await client.close()
    print("MongoDB connection closed")


app = FastAPI(
     title="AI Interviewer Hiring Platform",
     lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    # FIX: "*" let any website call this API from a visitor's browser.
    allow_origins=[settings.FRONTEND_URL, "http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Socket.IO
socket_app = socketio.ASGIApp(sio, app)

# Routers


@app.get("/")
async def root():
    """Friendly landing response so http://localhost:8000 shows something useful."""
    return {
        "status": "running",
        "message": "IntelliHire backend is running",
        "api_docs": "/docs",
        "health": "/health",
        "socket_namespaces": ["/ai", "/proc"],
    }


@app.get("/health")
def health() -> str:
    return "Working"


app.include_router(auth.router)
app.include_router(users.router)
app.include_router(jobs.router)
app.include_router(applications.router)
app.include_router(interviews.router)


if __name__ == "__main__":
    uvicorn.run("main:socket_app", host="0.0.0.0", port=8000, reload=True)
