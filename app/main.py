from __future__ import annotations

from fastapi import FastAPI
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .database import Base, engine
from .observability import RequestTimingLoggingMiddleware, add_exception_handlers
from .routers import health, campaigns
from .routers import members as members_router
from .routers import events as events_router
from .routers import bookings as bookings_router
from .routers import exports as exports_router
from .routers import analytics as analytics_router
from .routers import embeddings as embeddings_router
from .routers import devtools as devtools_router
from .routers import code_index as code_index_router
from .routers import class_types as class_types_router
from .routers import groups as groups_router
from .routers import payments as payments_router
from .routers import stripe_stub as stripe_router
from .routers import whatsapp_stub as whatsapp_router
from .routers import qr_stub as qr_router

# Ensure schema is present when the module is imported (helps tests using TestClient without lifespan)
Base.metadata.create_all(bind=engine)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize database schema on startup
    Base.metadata.create_all(bind=engine)
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    application = FastAPI(title="Boxing Admin API", version="0.1.0", lifespan=lifespan)

    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    application.add_middleware(RequestTimingLoggingMiddleware)

    add_exception_handlers(application)

    # Routers
    application.include_router(health.router)
    application.include_router(campaigns.router)
    application.include_router(members_router.router)
    application.include_router(events_router.router)
    application.include_router(bookings_router.router)
    application.include_router(exports_router.router)
    application.include_router(analytics_router.router)
    application.include_router(embeddings_router.router)
    application.include_router(devtools_router.router)
    application.include_router(code_index_router.router)
    application.include_router(class_types_router.router)
    application.include_router(groups_router.router)
    application.include_router(stripe_router.router)
    application.include_router(whatsapp_router.router)
    application.include_router(qr_router.router)
    application.include_router(payments_router.router)

    return application


app = create_app()


