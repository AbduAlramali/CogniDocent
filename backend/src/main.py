from fastapi import FastAPI, APIRouter
from dotenv import load_dotenv
from datetime import datetime, UTC
from src.exception_handlers import register_exception_handlers
from src.infra.python_logger import PythonLogger
from contextlib import asynccontextmanager
from starlette.middleware.cors import CORSMiddleware
from src.core.config import (
    get_app_settings,
    get_minio_settings,
    get_redis_settings,
)
from src.core.middleware import (
    RequestIdMiddleware,
    LoggingMiddleware,
)
from src.infra.clients import (
    minio_client,
    redis_client,
    httpx_client,
)
from src.routers.v1 import (
    chat,
    dev,
    document,
    message,
    notifications,
    project,
    provider,
    tts,
)

app_settings = get_app_settings()
logger = PythonLogger(name=app_settings.APP_NAME, app_state=app_settings.APP_ENV)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Application startup: Initializing resources")
    load_dotenv()

    logger.info(
        f"The App {app_settings.APP_NAME} is running in {app_settings.APP_ENV} mode"
    )

    # 1. Initialize HTTPX client
    httpx_client.initialize()

    # 2. Initialize Redis client
    try:
        redis_settings = get_redis_settings()
        await redis_client.initialize(str(redis_settings.redis_url))
        logger.info("Redis client initialized")
    except Exception as e:
        logger.warning("Redis client initialization skipped or failed", exc=e)

    # 3. Initialize MinIO client and configure buckets/events
    try:
        minio_settings = get_minio_settings()
        minio_client.initialize(minio_settings, app_settings)
        async with minio_client.get_client() as s3_client:
            await minio_client.setup_minio_events(s3_client, minio_settings, logger)
        logger.info("MinIO client initialized and buckets configured")
    except Exception as e:
        logger.warning("MinIO client initialization skipped or failed", exc=e)

    yield

    logger.info("Application shutdown: Cleaning up resources")
    if redis_client.client is not None:
        await redis_client.close()
    if httpx_client.client is not None:
        await httpx_client.close()
    await minio_client.close()



app = FastAPI(
    title=get_app_settings().APP_NAME,
    version=get_app_settings().APP_VERSION,
    description=get_app_settings().APP_DESCRIPTION,
    root_path=get_app_settings().APP_ROOT_PATH,
    docs_url=get_app_settings().APP_DOCS_PATH,
    lifespan=lifespan,
)

app.add_middleware(RequestIdMiddleware)
app.add_middleware(LoggingMiddleware)

# CORS Configuration
# Note: When allow_credentials=True, allow_origins cannot be ["*"]
origins = [
    "http://localhost:8080",
    "http://127.0.0.1:8080",
    "http://localhost:5173",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    # Allow any localhost/127.0.0.1 port, any ngrok tunnel, and common private IP ranges for local network dev
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1|0\.0\.0\.0)(:\d+)?|"
    r"https?://.*\.ngrok-free\.dev|"
    r"https?://(192\.168\.\d+\.\d+|10\.\d+\.\d+\.\d+|172\.(1[6-9]|2[0-9]|3[01])\.\d+\.\d+)(:\d+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app, logger)


@app.get("/health", tags=["System"])
async def health_check():
    """
    Health check endpoint.
    Returns 200 OK if the service is up.
    """
    return {"status": "healthy", "timestamp": datetime.now(UTC), "version": "1.0.0"}


v1_router = APIRouter(prefix="/v1")
v1_router.include_router(project.router)
v1_router.include_router(chat.router)
v1_router.include_router(message.router)
v1_router.include_router(document.router)
v1_router.include_router(provider.router)
v1_router.include_router(tts.router)
v1_router.include_router(notifications.router)

if get_app_settings().APP_ENV == "development":
    v1_router.include_router(dev.router)
    logger.warning("Development endpoints are enabled!")

app.include_router(v1_router)
