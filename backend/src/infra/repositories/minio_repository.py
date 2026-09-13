import aioboto3
from botocore.exceptions import ClientError
from src.core.interfaces.iobject_repository import IObjectRepository
from src.core.interfaces.ilogger import ILogger
from src.core.exceptions.object_storage_exceptions import (
    ObjectRepositoryError,
    ObjectDownloadError,
    ObjectNotFoundError,
    ObjectUploadError,
)
from typing import List


class MinioObjectRepository(IObjectRepository):
    def __init__(
        self,
        session: aioboto3.Session,
        internal_config: dict,
        external_config: dict,
        bucket_name: str,
        logger: ILogger,
    ):
        self._session = session
        self._internal_config = internal_config
        self._external_config = external_config
        self._bucket_name = bucket_name
        self._logger = logger

    async def _ensure_bucket_exists(self):
        """Ensure the bucket exists on initialization using the internal network."""
        async with self._session.client("s3", **self._internal_config) as s3:
            try:
                await s3.head_bucket(Bucket=self._bucket_name)
            except ClientError as e:
                error_code = e.response.get("Error", {}).get("Code")
                if (
                    error_code == "404"
                    or e.response.get("ResponseMetadata", {}).get("HTTPStatusCode")
                    == 404
                ):
                    self._logger.info("Creating bucket", bucket_name=self._bucket_name)
                    try:
                        await s3.create_bucket(Bucket=self._bucket_name)
                    except ClientError as create_err:
                        self._logger.error(
                            "Failed to create Minio bucket",
                            bucket_name=self._bucket_name,
                            exc=create_err,
                        )
                        raise ObjectRepositoryError(
                            "Failed to initialize object storage."
                        ) from create_err
                else:
                    self._logger.error(
                        "Failed to initialize Minio bucket",
                        bucket_name=self._bucket_name,
                        exc=e,
                    )
                    raise ObjectRepositoryError(
                        "Failed to initialize object storage."
                    ) from e

    async def get_upload_url(
        self, object_name: str, expires_in_minutes: int = 60, bucket: str | None = None
    ) -> str:
        target_bucket = bucket or self._bucket_name
        self._logger.info(
            "Generating presigned upload URL",
            object_name=object_name,
            bucket=target_bucket,
        )
        async with self._session.client("s3", **self._external_config) as s3:
            try:
                return await s3.generate_presigned_url(
                    ClientMethod="put_object",
                    Params={
                        "Bucket": target_bucket,
                        "Key": object_name,
                    },
                    ExpiresIn=expires_in_minutes * 60,
                )
            except ClientError as err:
                self._logger.error(
                    "Failed to generate upload URL", object_name=object_name, exc=err
                )
                raise ObjectUploadError("Failed to generate upload URL.") from err

    async def get_download_url(
        self, object_name: str, expires_in_minutes: int = 60, bucket: str | None = None
    ) -> str:
        target_bucket = bucket or self._bucket_name
        self._logger.info(
            "Generating presigned download URL",
            object_name=object_name,
            bucket=target_bucket,
        )
        async with self._session.client("s3", **self._external_config) as s3:
            try:
                return await s3.generate_presigned_url(
                    ClientMethod="get_object",
                    Params={
                        "Bucket": target_bucket,
                        "Key": object_name,
                    },
                    ExpiresIn=expires_in_minutes * 60,
                )
            except ClientError as err:
                self._logger.error(
                    "Failed to generate download URL", object_name=object_name, exc=err
                )
                raise ObjectDownloadError("Failed to generate download URL.") from err

    async def upload_object(
        self,
        object_name: str,
        data: bytes,
        content_type: str = "application/octet-stream",
        bucket: str | None = None,
    ) -> None:
        target_bucket = bucket or self._bucket_name
        self._logger.info(
            "Uploading object directly", object_name=object_name, bucket=target_bucket
        )
        async with self._session.client("s3", **self._internal_config) as s3:
            try:
                await s3.put_object(
                    Bucket=target_bucket,
                    Key=object_name,
                    Body=data,
                    ContentType=content_type,
                )
                self._logger.info(
                    "Object uploaded successfully", object_name=object_name
                )
            except ClientError as e:
                self._logger.error(
                    "Failed to upload object", object_name=object_name, exc=e
                )
                raise ObjectRepositoryError("Failed to upload object.") from e

    async def download_object(
        self, object_name: str, bucket: str | None = None
    ) -> bytes:
        target_bucket = bucket or self._bucket_name
        self._logger.info(
            "Downloading object directly", object_name=object_name, bucket=target_bucket
        )
        async with self._session.client("s3", **self._internal_config) as s3:
            try:
                response = await s3.get_object(Bucket=target_bucket, Key=object_name)
                return await response["Body"].read()
            except ClientError as e:
                error_code = e.response.get("Error", {}).get("Code")
                if (
                    error_code in ["NoSuchKey", "404"]
                    or e.response.get("ResponseMetadata", {}).get("HTTPStatusCode")
                    == 404
                ):
                    self._logger.warning(
                        "Object not found for download", object_name=object_name
                    )
                    raise ObjectNotFoundError(object_name)
                self._logger.error(
                    "Failed to download object", object_name=object_name, exc=e
                )
                raise ObjectRepositoryError("Failed to download object.") from e

    async def check_exists(self, object_name: str, bucket: str | None = None) -> bool:
        target_bucket = bucket or self._bucket_name
        async with self._session.client("s3", **self._internal_config) as s3:
            try:
                await s3.head_object(Bucket=target_bucket, Key=object_name)
                return True
            except ClientError as err:
                error_code = err.response.get("Error", {}).get("Code")
                if (
                    error_code in ["NoSuchKey", "404"]
                    or err.response.get("ResponseMetadata", {}).get("HTTPStatusCode")
                    == 404
                ):
                    return False
                self._logger.error(
                    "Failed to check object existence", object_name=object_name, exc=err
                )
                raise ObjectDownloadError("Failed to check object existence.") from err

    async def delete_object(self, object_name: str, bucket: str | None = None) -> None:
        target_bucket = bucket or self._bucket_name
        self._logger.info(
            "Deleting object", object_name=object_name, bucket=target_bucket
        )
        async with self._session.client("s3", **self._internal_config) as s3:
            try:
                await s3.delete_object(Bucket=target_bucket, Key=object_name)
            except ClientError as err:
                error_code = err.response.get("Error", {}).get("Code")
                if (
                    error_code in ["NoSuchKey", "404"]
                    or err.response.get("ResponseMetadata", {}).get("HTTPStatusCode")
                    == 404
                ):
                    self._logger.warning(
                        "Object not found for deletion (skipping)",
                        object_name=object_name,
                    )
                    return
                self._logger.error(
                    "Failed to delete object", object_name=object_name, exc=err
                )
                raise ObjectRepositoryError("Failed to delete object.") from err

    async def copy_object(
        self,
        source_key: str,
        destination_key: str,
        source_bucket: str | None = None,
        target_bucket: str | None = None,
    ) -> None:
        s_bucket = source_bucket or self._bucket_name
        t_bucket = target_bucket or self._bucket_name
        self._logger.info(
            "Copying object",
            source=source_key,
            source_bucket=s_bucket,
            destination=destination_key,
            target_bucket=t_bucket,
        )
        async with self._session.client("s3", **self._internal_config) as s3:
            try:
                copy_source = {"Bucket": s_bucket, "Key": source_key}
                await s3.copy_object(
                    Bucket=t_bucket,
                    CopySource=copy_source,
                    Key=destination_key,
                )
            except ClientError as e:
                self._logger.error(
                    "Failed to copy object",
                    source=source_key,
                    destination=destination_key,
                    exc=e,
                )
                raise ObjectRepositoryError("Failed to copy object.") from e

    async def list_objects(self, prefix: str, bucket: str | None = None) -> List[str]:
        target_bucket = bucket or self._bucket_name
        self._logger.info("Listing objects", prefix=prefix, bucket=target_bucket)
        async with self._session.client("s3", **self._internal_config) as s3:
            try:
                paginator = s3.get_paginator("list_objects_v2")
                object_keys = []
                async for page in paginator.paginate(
                    Bucket=target_bucket, Prefix=prefix
                ):
                    if "Contents" in page:
                        for obj in page["Contents"]:
                            object_keys.append(obj["Key"])
                return object_keys
            except ClientError as err:
                self._logger.error("Failed to list objects", prefix=prefix, exc=err)
                raise ObjectRepositoryError("Failed to list objects.") from err

    def get_public_url(self, bucket: str, key: str) -> str:
        """
        Constructs a public URL for an Minio object.
        Uses the EXTERNAL_ENDPOINT for frontend access.
        """
        if not key or key.startswith(("http://", "https://")):
            return key

        endpoint = self._external_config.get("endpoint_url", "localhost:9000").rstrip(
            "/"
        )
        return f"{endpoint}/{bucket}/{key}"

    def format_thumbnails_urls(
        self, thumbnails: dict[str, str] | None, bucket: str
    ) -> dict[str, str] | None:
        """
        Converts object paths in thumbnails dict to full public URLs.
        """
        if not thumbnails:
            return None

        return {
            tier: self.get_public_url(bucket, path) for tier, path in thumbnails.items()
        }
