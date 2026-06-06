"""
S3 operations for the UniversalDocumentRepository bucket.

Naming convention inside the bucket:
  {user_id}/                        ← user "folder" (placeholder object)
  {user_id}/{file_id}/{filename}    ← uploaded file

The container must have an IAM role (or instance profile) that grants
s3:PutObject, s3:GetObject, s3:DeleteObject, s3:ListBucket on the bucket.
"""

import uuid

import boto3
from botocore.exceptions import ClientError

from config import Config

_s3 = boto3.client("s3", region_name=Config.AWS_REGION)


# ---------------------------------------------------------------------------
# User prefix
# ---------------------------------------------------------------------------

def create_user_prefix(user_id: str) -> None:
    """
    Create a zero-byte placeholder object that represents the user's 'folder'.
    Idempotent – safe to call on every login.
    """
    _s3.put_object(
        Bucket=Config.S3_BUCKET_NAME,
        Key=f"{user_id}/.keep",
        Body=b"",
        ContentType="application/octet-stream",
    )


# ---------------------------------------------------------------------------
# File upload
# ---------------------------------------------------------------------------

def upload_file(
    user_id: str,
    file_obj,
    filename: str,
    content_type: str,
) -> dict:
    """
    Upload *file_obj* to the user's S3 prefix.

    Returns:
        {
          "file_id":  str,   # UUID used as DynamoDB sort-key
          "s3_key":   str,   # key inside the bucket
          "s3_path":  str,   # full s3:// URI
          "filename": str,
        }
    """
    file_id = str(uuid.uuid4())
    s3_key = f"{user_id}/{file_id}/{filename}"

    _s3.upload_fileobj(
        file_obj,
        Config.S3_BUCKET_NAME,
        s3_key,
        ExtraArgs={"ContentType": content_type},
    )

    return {
        "file_id": file_id,
        "s3_key": s3_key,
        "s3_path": f"s3://{Config.S3_BUCKET_NAME}/{s3_key}",
        "filename": filename,
    }


# ---------------------------------------------------------------------------
# Presigned download URL
# ---------------------------------------------------------------------------

def generate_presigned_download_url(
    s3_key: str,
    filename: str,
    expiration_seconds: int = 3600,
) -> str:
    """
    Return a presigned GET URL that forces the browser to download the file
    under its original filename. Valid for *expiration_seconds* (default 1 h).
    """
    url: str = _s3.generate_presigned_url(
        "get_object",
        Params={
            "Bucket": Config.S3_BUCKET_NAME,
            "Key": s3_key,
            "ResponseContentDisposition": f'attachment; filename="{filename}"',
        },
        ExpiresIn=expiration_seconds,
    )
    return url


# ---------------------------------------------------------------------------
# Delete
# ---------------------------------------------------------------------------

def delete_file(s3_key: str) -> None:
    """Permanently delete a single object from S3."""
    try:
        _s3.delete_object(Bucket=Config.S3_BUCKET_NAME, Key=s3_key)
    except ClientError as exc:
        # Log but don't raise – DynamoDB record will still be cleaned up
        error_code = exc.response["Error"]["Code"]
        raise RuntimeError(f"S3 delete failed ({error_code}): {s3_key}") from exc
