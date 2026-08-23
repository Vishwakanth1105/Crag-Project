"""S3-compatible object storage client backed by MinIO via boto3."""

from __future__ import annotations

import io
from collections.abc import Generator

import boto3
from botocore.client import Config
from botocore.exceptions import BotoCoreError, ClientError

from src.config import Settings, get_settings
from src.exceptions import StorageError


class StorageClient:
    """Thin wrapper around an S3/MinIO client with idempotent bucket setup."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.client = boto3.client(
            "s3",
            endpoint_url=(
                f"{'https' if self.settings.minio_secure else 'http'}://"
                f"{self.settings.minio_endpoint}"
            ),
            aws_access_key_id=self.settings.minio_access_key,
            aws_secret_access_key=self.settings.minio_secret_key,
            config=Config(
                signature_version="s3v4",
                connect_timeout=2,
                read_timeout=5,
                retries={"max_attempts": 2},
            ),
            region_name="us-east-1",
        )

    def ensure_bucket(self) -> None:
        try:
            self.client.head_bucket(Bucket=self.settings.minio_bucket)
        except ClientError:
            self.client.create_bucket(Bucket=self.settings.minio_bucket)

    def upload_bytes(
        self, key: str, data: bytes, *, content_type: str = "application/octet-stream"
    ) -> None:
        try:
            self.client.put_object(
                Bucket=self.settings.minio_bucket,
                Key=key,
                Body=data,
                ContentType=content_type,
            )
        except (BotoCoreError, ClientError) as exc:
            raise StorageError(f"Unable to upload object: {key}") from exc

    def download(self, key: str) -> Generator[bytes, None, None]:
        try:
            response = self.client.get_object(Bucket=self.settings.minio_bucket, Key=key)
            yield from response["Body"].iter_chunks(chunk_size=1024 * 1024)
        except (BotoCoreError, ClientError) as exc:
            raise StorageError(f"Unable to download object: {key}") from exc

    def download_bytes(self, key: str) -> bytes:
        buffer = io.BytesIO()
        for chunk in self.download(key):
            buffer.write(chunk)
        return buffer.getvalue()

    def delete_object(self, key: str) -> None:
        try:
            self.client.delete_object(Bucket=self.settings.minio_bucket, Key=key)
        except (BotoCoreError, ClientError) as exc:
            raise StorageError(f"Unable to delete object: {key}") from exc

    def ready(self) -> tuple[bool, str | None]:
        try:
            self.client.list_buckets()
            return True, None
        except Exception as exc:  # pragma: no cover - external service specific
            return False, str(exc)
