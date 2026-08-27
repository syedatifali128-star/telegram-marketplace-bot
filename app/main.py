from __future__ import annotations

import logging
import asyncio
from broadcast import send_advertisements

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse

from app.config import settings
from app.core.security import NotAuthenticated
from app.database.connection import init_db
from app.dashboard.auth_routes import router as auth_router
from app.dashboard.routes import router as dashboard_router

logging.basicConfig(
    level=settings.log_level,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler(settings.log_file)],
)
logger = logging.getLogger("app")

app = FastAPI(title="Telegram Marketplace Manager", version="0.1.0")

@app.exception_handler(NotAuthenticated)
def handle_not_authenticated(request: Request, exc: NotAuthenticated):
    return RedirectResponse(url="/login", status_code=303)


app.include_router(auth_router)
app.include_router(dashboard_router)


@app.on_event("startup")
async def on_startup() -> None:
    # 1. Initialize the database 
    init_db()
    logger.info("Database ready at %s", settings.database_url) 

    # 2. Launch the broadcaster loop as a background task 
    asyncio.create_task(send_advertisements())  


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "env": settings.app_env}


 import os
 import uvicorn

# Bind port for Render
port = int(os.environ.get("PORT", 10000))
uvicorn.run(app, host="0.0.0.0", port=port)
