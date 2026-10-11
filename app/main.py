"""FastAPI application entry point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from .database import Base, engine
from .routers import applications, auth, stats


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Fine for a small project. For real deployments, manage the schema with migrations (Alembic).
    Base.metadata.create_all(engine)
    yield


app = FastAPI(
    title="Job Tracker API",
    version="1.0.0",
    description="Track job applications, enforce a valid status workflow, and see pipeline statistics.",
    lifespan=lifespan,
)

app.include_router(auth.router)
app.include_router(applications.router)
app.include_router(stats.router)


@app.get("/health", tags=["meta"])
def health():
    return {"status": "ok"}
