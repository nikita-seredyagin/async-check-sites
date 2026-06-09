from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.database import create_tables
from app.routers import checks, sites


@asynccontextmanager
async def lifespan(application: FastAPI):
    await create_tables()
    yield


app = FastAPI(
    title="Async Site Checker",
    description="Service for monitoring website availability",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(sites.router)
app.include_router(checks.router)