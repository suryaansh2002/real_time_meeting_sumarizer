from contextlib import asynccontextmanager
from typing import AsyncGenerator
from fastapi import FastAPI

from app.dependencies.meetings import session_repository
from app.handlers import meetings
from app.settings.meetings import settings_instance

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # Startup
    repo = session_repository(settings=settings_instance())
    await repo.initialize()
    yield
    # Shutdown
    await repo.close()

def create_app():
    app = FastAPI(docs_url="/", lifespan=lifespan)

    # Routers
    app.include_router(meetings.router)

    return app
