"""
storage.py — S3 / Cloudflare R2 Storage Utilities  (Phase 5)
==============================================================

Handles cloud storage for video uploads and processed shorts.
Supports both AWS S3 and Cloudflare R2 (S3-compatible).

Configure via environment variables:
  S3_BUCKET         — bucket name
  S3_REGION         — e.g. us-east-1
  S3_ENDPOINT       — custom endpoint for R2 / MinIO
  AWS_ACCESS_KEY_ID — access key
  AWS_SECRET_ACCESS_KEY — secret key
"""

import logging
import os
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Configuration
S3_BUCKET = os.getenv("S3_BUCKET", "video-shorts-uploads")
S3_REGION = os.getenv("S3_REGION", "us-east-1")
S3_ENDPOINT = os.getenv("S3_ENDPOINT", "")  # Set for R2 / MinIO


def _get_s3_client():
    """Create a boto3 S3 client with optional custom endpoint."""
    try:
        import boto3
    except ImportError:
        raise ImportError("boto3 required: pip install boto3")

    kwargs = {"region_name": S3_REGION}
    if S3_ENDPOINT:
        kwargs["endpoint_url"] = S3_ENDPOINT

    return boto3.client("s3", **kwargs)


def generate_presigned_upload_url(
    filename: str,
    content_type: str = "video/mp4",
    expires_in: int = 3600,
) -> dict:
    """
    Generate a pre-signed URL for direct browser-to-S3 upload.

    This avoids routing large video files through our API server.

    Args:
        filename:     Desired S3 key / filename.
        content_type: MIME type of the file.
        expires_in:   URL expiry in seconds (default 1 hour).

    Returns:
        dict with "upload_url" and "key".
    """
    client = _get_s3_client()
    key = f"uploads/{filename}"

    url = client.generate_presigned_url(
        "put_object",
        Params={
            "Bucket": S3_BUCKET,
            "Key": key,
            "ContentType": content_type,
        },
        ExpiresIn=expires_in,
    )

    return {"upload_url": url, "key": key}


def generate_presigned_download_url(
    key: str,
    expires_in: int = 3600,
) -> str:
    """
    Generate a pre-signed URL for downloading a processed video.

    Args:
        key:        S3 object key.
        expires_in: URL expiry in seconds.

    Returns:
        Pre-signed download URL string.
    """
    client = _get_s3_client()

    return client.generate_presigned_url(
        "get_object",
        Params={"Bucket": S3_BUCKET, "Key": key},
        ExpiresIn=expires_in,
    )


def upload_file(local_path: str, s3_key: Optional[str] = None) -> str:
    """
    Upload a local file to S3.

    Args:
        local_path: Path to the file on disk.
        s3_key:     Destination key in S3. Auto-derived from filename if None.

    Returns:
        The S3 key of the uploaded file.
    """
    client = _get_s3_client()

    if s3_key is None:
        s3_key = f"shorts/{Path(local_path).name}"

    logger.info(f"Uploading {local_path} → s3://{S3_BUCKET}/{s3_key}")

    client.upload_file(
        local_path,
        S3_BUCKET,
        s3_key,
        ExtraArgs={"ContentType": "video/mp4"},
    )

    return s3_key


def download_file(s3_key: str, local_path: str) -> str:
    """
    Download a file from S3 to local disk.

    Args:
        s3_key:     S3 object key.
        local_path: Where to save locally.

    Returns:
        The local path.
    """
    client = _get_s3_client()

    logger.info(f"Downloading s3://{S3_BUCKET}/{s3_key} → {local_path}")
    client.download_file(S3_BUCKET, s3_key, local_path)

    return local_path


def delete_file(s3_key: str):
    """Delete a file from S3."""
    client = _get_s3_client()
    client.delete_object(Bucket=S3_BUCKET, Key=s3_key)
    logger.info(f"Deleted s3://{S3_BUCKET}/{s3_key}")
