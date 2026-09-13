from __future__ import annotations
import aioboto3
import json
from contextlib import asynccontextmanager
from typing import Any
from botocore.config import Config
from botocore.exceptions import ClientError
from src.core.config import MinioSettings, AppSettings
from src.core.interfaces.ilogger import ILogger

# Global session to be shared
session: aioboto3.Session | None = None

# Configs for internal/external access
internal_config: dict[str, Any] = {}
external_config: dict[str, Any] = {}


async def setup_minio_events(minio_client: Any, settings: MinioSettings, logger: ILogger) -> None:
    """
    Configures Minio buckets, policies, and notification webhooks.
    """
    # 1. Ensure all buckets exist
    required_buckets = [
        settings.INCOMING_UPLOADS_BUCKET,
        settings.QUARANTINE_BUCKET,
        settings.TRUSTED_BUCKET,
        settings.INFECTED_BUCKET,
        settings.THUMBNAILS_BUCKET,
        "resources",
    ]

    public_buckets = [
        settings.THUMBNAILS_BUCKET,
        "resources",
    ]

    for bucket in required_buckets:
        try:
            await minio_client.head_bucket(Bucket=bucket)
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code")
            http_status = e.response.get("ResponseMetadata", {}).get("HTTPStatusCode")
            if error_code in ["404", "NoSuchBucket"] or http_status == 404:
                logger.info(f"Creating missing bucket: {bucket}")
                await minio_client.create_bucket(Bucket=bucket)
            else:
                raise

    # 2. Set public policy for public buckets
    for bucket in public_buckets:
        policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {"AWS": ["*"]},
                    "Action": ["s3:GetObject"],
                    "Resource": [f"arn:aws:s3:::{bucket}/*"],
                }
            ],
        }
        await minio_client.put_bucket_policy(Bucket=bucket, Policy=json.dumps(policy))
        logger.info(f"Set public policy for bucket: {bucket}")

    # 3. Configure Webhooks
    buckets_to_monitor = [
        (settings.INCOMING_UPLOADS_BUCKET, "incoming-uploads"),
        (settings.QUARANTINE_BUCKET, "quarantine-upload"),
    ]

    webhook_arn = "arn:minio:sqs::backend:webhook"

    for bucket_name, event_id in buckets_to_monitor:
        notification_configuration = {
            "QueueConfigurations": [
                {
                    "Id": event_id,
                    "QueueArn": webhook_arn,
                    "Events": ["s3:ObjectCreated:Put"],
                }
            ]
        }

        try:
            await minio_client.put_bucket_notification_configuration(
                Bucket=bucket_name, NotificationConfiguration=notification_configuration
            )
            logger.info(
                "Successfully bound Minio events",
                bucket_name=bucket_name,
                webhook_arn=webhook_arn,
            )
        except ClientError as exc:
            logger.warning(
                "Failed to configure Minio event webhook",
                bucket_name=bucket_name,
                webhook_arn=webhook_arn,
                exc=exc,
            )


def initialize(
    minio_settings: MinioSettings | None = None,
    app_settings: AppSettings | None = None,
) -> None:
    """
    Initializes the global minio_client session and configurations.
    This can be called from the FastAPI lifespan or from a Celery worker.
    """
    global session, internal_config, external_config

    if session is not None and internal_config and external_config:
        return

    if minio_settings is None:
        from src.core.config import get_minio_settings

        minio_settings = get_minio_settings()

    if app_settings is None:
        from src.core.config import get_app_settings

        app_settings = get_app_settings()

    # Internal tasks (Backend -> MinIO)
    minio_internal_endpoint = minio_settings.ENDPOINT
    if minio_internal_endpoint and not minio_internal_endpoint.startswith(
        ("http://", "https://")
    ):
        minio_internal_protocol = "https" if minio_settings.SECURE else "http"
        minio_internal_endpoint = (
            f"{minio_internal_protocol}://{minio_internal_endpoint}"
        )

    # URL generation (Browser -> MinIO)
    minio_url_endpoint = minio_settings.EXTERNAL_ENDPOINT
    if minio_url_endpoint and not minio_url_endpoint.startswith(
        ("http://", "https://")
    ):
        minio_url_protocol = "https" if app_settings.APP_ENV == "production" else "http"
        minio_url_endpoint = f"{minio_url_protocol}://{minio_url_endpoint}"

    # Initialize aioboto3 session and configs
    session = aioboto3.Session()
    s3_config = Config(
        signature_version="s3v4",
        s3={"addressing_style": "path"},
    )

    internal_config = {
        "endpoint_url": minio_internal_endpoint,
        "aws_access_key_id": minio_settings.ACCESS_KEY,
        "aws_secret_access_key": minio_settings.SECRET_KEY,
        "region_name": minio_settings.REGION,
        "config": s3_config,
        "use_ssl": minio_settings.SECURE,
    }
    if minio_settings.AUTH_TOKEN:
        internal_config["aws_session_token"] = minio_settings.AUTH_TOKEN

    external_config = {
        "endpoint_url": minio_url_endpoint,
        "aws_access_key_id": minio_settings.ACCESS_KEY,
        "aws_secret_access_key": minio_settings.SECRET_KEY,
        "region_name": minio_settings.REGION,
        "config": s3_config,
        "use_ssl": minio_settings.SECURE or app_settings.APP_ENV == "production",
    }
    if minio_settings.AUTH_TOKEN:
        external_config["aws_session_token"] = minio_settings.AUTH_TOKEN


@asynccontextmanager
async def get_client(external: bool = False):
    """
    Async context manager yielding an S3 client using the global session.
    Defaults to the internal client, with external client option when needed.
    """
    global session, internal_config, external_config
    if session is None:
        initialize()
    config = external_config if external else internal_config
    async with session.client("s3", **config) as s3:
        yield s3


@asynccontextmanager
async def get_internal_client():
    """Convenience context manager for the internal MinIO client."""
    async with get_client(external=False) as s3:
        yield s3


@asynccontextmanager
async def get_external_client():
    """Convenience context manager for the external MinIO client."""
    async with get_client(external=True) as s3:
        yield s3


async def close() -> None:
    """
    Cleans up session resources on shutdown.
    """
    global session
    session = None


