"""
DynamoDB operations for file metadata.

Table schema
------------
Table name   : FileMetadata  (configurable via DYNAMODB_TABLE_NAME env var)
Partition key: userId  (String) – Cognito sub
Sort key     : fileId  (String) – UUID generated at upload time

Attributes
----------
fileName     String   Original filename
s3Path       String   Full s3:// URI
s3Key        String   Key inside the bucket (needed for presigned URLs / delete)
uploadDate   String   ISO-8601 UTC timestamp
annotation   String   User-supplied text annotation (may be empty)
fileSize     Number   Size in bytes
contentType  String   MIME type

The IAM role attached to the container must grant:
  dynamodb:PutItem, dynamodb:GetItem, dynamodb:Query,
  dynamodb:UpdateItem, dynamodb:DeleteItem
on this table.
"""

from datetime import datetime, timezone

import boto3
from boto3.dynamodb.conditions import Key

from config import Config

_dynamodb = boto3.resource("dynamodb", region_name=Config.AWS_REGION)
_table = _dynamodb.Table(Config.DYNAMODB_TABLE_NAME)


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------

def create_file_record(
    *,
    user_id: str,
    file_id: str,
    filename: str,
    s3_path: str,
    s3_key: str,
    file_size: int,
    content_type: str,
    annotation: str = "",
) -> dict:
    """Insert a new file metadata record and return it."""
    item = {
        "userId": user_id,
        "fileId": file_id,
        "fileName": filename,
        "s3Path": s3_path,
        "s3Key": s3_key,
        "uploadDate": datetime.now(timezone.utc).isoformat(),
        "annotation": annotation,
        "fileSize": file_size,
        "contentType": content_type,
    }
    _table.put_item(Item=item)
    return item


# ---------------------------------------------------------------------------
# Read
# ---------------------------------------------------------------------------

def get_user_files(user_id: str) -> list[dict]:
    """Return all file records for a user, sorted by uploadDate descending."""
    response = _table.query(
        KeyConditionExpression=Key("userId").eq(user_id)
    )
    items: list[dict] = response.get("Items", [])
    # Sort newest-first in application layer (avoids a GSI for now)
    items.sort(key=lambda x: x.get("uploadDate", ""), reverse=True)
    return items


def get_file(user_id: str, file_id: str) -> dict | None:
    """Return a single file record, or None if not found."""
    response = _table.get_item(
        Key={"userId": user_id, "fileId": file_id}
    )
    return response.get("Item")


# ---------------------------------------------------------------------------
# Update
# ---------------------------------------------------------------------------

def update_annotation(user_id: str, file_id: str, annotation: str) -> dict:
    """
    Update the annotation text for a file.
    Returns the updated item attributes.
    """
    response = _table.update_item(
        Key={"userId": user_id, "fileId": file_id},
        UpdateExpression="SET annotation = :a, updatedAt = :u",
        ExpressionAttributeValues={
            ":a": annotation,
            ":u": datetime.now(timezone.utc).isoformat(),
        },
        ReturnValues="ALL_NEW",
    )
    return response["Attributes"]


# ---------------------------------------------------------------------------
# Delete
# ---------------------------------------------------------------------------

def delete_file_record(user_id: str, file_id: str) -> None:
    """Remove a file metadata record from DynamoDB."""
    _table.delete_item(Key={"userId": user_id, "fileId": file_id})
