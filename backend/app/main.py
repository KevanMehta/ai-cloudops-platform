import logging
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import Counter, Histogram

from app.config import settings
from app.logging_config import request_id_context, setup_logging
from app.routers import api

setup_logging(settings.log_level)
logger = logging.getLogger(__name__)

HTTP_REQUESTS = Counter(
    "cloudops_http_requests_total", "HTTP requests", ["method", "route", "status"]
)
HTTP_DURATION = Histogram(
    "cloudops_http_request_duration_seconds", "HTTP request duration", ["method", "route"]
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting %s v%s", settings.app_name, settings.app_version)
    yield
    logger.info("Shutting down")


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Cloud operations reference implementation with demo, connected, and offline modes.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def observe_request(request: Request, call_next):
    request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
    token = request_id_context.set(request_id)
    started = time.perf_counter()
    status = 500
    try:
        response = await call_next(request)
        status = response.status_code
        response.headers["x-request-id"] = request_id
        return response
    finally:
        route = request.scope.get("route")
        route_path = getattr(route, "path", "unmatched")
        elapsed = time.perf_counter() - started
        HTTP_REQUESTS.labels(request.method, route_path, str(status)).inc()
        HTTP_DURATION.labels(request.method, route_path).observe(elapsed)
        logger.info(
            "HTTP request completed",
            extra={"method": request.method, "route": route_path, "status": status, "duration_ms": round(elapsed * 1000, 2)},
        )
        request_id_context.reset(token)

app.include_router(api.router)
