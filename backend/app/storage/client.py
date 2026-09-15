"""
Supabase Storage client — S3-compatible object storage.

Wraps boto3 (AWS SDK) which works with Supabase Storage's S3-compatible API.
All storage operations are isolated here so the rest of the code is testable
without needing a real S3 bucket.

Key behaviours:
- upload_pdf()  → uploads bytes, returns (storage_key, presigned_url)
- get_presigned_url() → generates a short-lived read URL for the frontend
- download_pdf() → streams bytes for the processing pipeline
- delete_pdf()  → removes the object (called on document delete)

The storage_key format: pdfs/{user_id}/{document_id}/{filename}
This keeps each user's files isolated and makes bucket browsing readable.
"""

from __future__ import annotations

import io
import mimetypes
import uuid
from typing import Tuple

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError

from app.core.config import get_settings


def _get_s3_client():
    """Create a new boto3 S3 client using Supabase Storage endpoint."""
    settings = get_settings()
    return boto3.client(
        "s3",
        endpoint_url=settings.STORAGE_ENDPOINT,
        aws_access_key_id=settings.STORAGE_ACCESS_KEY,
        aws_secret_access_key=settings.STORAGE_SECRET_KEY,
        region_name=settings.STORAGE_REGION,
        config=Config(signature_version="s3v4"),
    )


class StorageClient:
    """
    Thin wrapper around boto3 S3 client for Supabase Storage.

    All methods are synchronous because boto3 is synchronous.
    They are called from Celery worker threads (not async FastAPI handlers).
    The upload endpoint calls upload_pdf() synchronously before dispatching
    the Celery task.
    """

    def __init__(self):
        self._client = _get_s3_client()
        self._bucket = get_settings().STORAGE_BUCKET

    def upload_pdf(
        self,
        *,
        user_id: uuid.UUID,
        document_id: uuid.UUID,
        filename: str,
        file_bytes: bytes,
    ) -> Tuple[str, str]:
        """
        Upload a PDF to storage.

        Returns:
            (storage_key, presigned_url)
            storage_key: the object key (persisted in DB)
            presigned_url: a short-lived (1h) pre-signed URL for direct download
        """
        # Sanitise filename for safe storage key
        safe_name = filename.replace(" ", "_").replace("/", "_")
        storage_key = f"pdfs/{user_id}/{document_id}/{safe_name}"

        content_type = mimetypes.guess_type(filename)[0] or "application/pdf"

        self._client.put_object(
            Bucket=self._bucket,
            Key=storage_key,
            Body=file_bytes,
            ContentType=content_type,
            Metadata={
                "user_id": str(user_id),
                "document_id": str(document_id),
                "original_filename": filename,
            },
        )

        presigned_url = self._client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self._bucket, "Key": storage_key},
            ExpiresIn=3600,  # 1 hour
        )

        return storage_key, presigned_url

    def download_pdf(self, storage_key: str) -> bytes:
        """Download PDF bytes from storage (used by processing pipeline)."""
        try:
            response = self._client.get_object(Bucket=self._bucket, Key=storage_key)
            return response["Body"].read()
        except ClientError as e:
            raise FileNotFoundError(
                f"PDF not found in storage: {storage_key}"
            ) from e

    def get_presigned_url(self, storage_key: str, expires_in: int = 3600) -> str:
        """Generate a new pre-signed URL for an existing storage object."""
        return self._client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self._bucket, "Key": storage_key},
            ExpiresIn=expires_in,
        )

    def delete_pdf(self, storage_key: str) -> None:
        """Delete an object from storage. Silently ignores missing objects."""
        try:
            self._client.delete_object(Bucket=self._bucket, Key=storage_key)
        except ClientError:
            pass  # Already deleted or doesn't exist — that's fine
