"""
File management routes.

GET    /api/files/              – list all files for the authenticated user
POST   /api/files/upload        – upload a new file (multipart/form-data)
GET    /api/files/<fileId>/download – get a presigned download URL (1-hour TTL)
PUT    /api/files/<fileId>/annotation – add / update annotation text
DELETE /api/files/<fileId>      – delete file from S3 and DynamoDB

All routes require a valid Cognito Bearer token.
"""

from flask import Blueprint, g, jsonify, request

from middleware.auth import require_auth
from services import dynamodb_service, s3_service

files_bp = Blueprint("files", __name__)

_MAX_UPLOAD_BYTES = 500 * 1024 * 1024  # 500 MB guard


# ---------------------------------------------------------------------------
# List files
# ---------------------------------------------------------------------------

@files_bp.route("/", methods=["GET"])
@require_auth
def list_files():
    files = dynamodb_service.get_user_files(g.user_id)
    return jsonify({"files": files})


# ---------------------------------------------------------------------------
# Upload
# ---------------------------------------------------------------------------

@files_bp.route("/upload", methods=["POST"])
@require_auth
def upload_file():
    if "file" not in request.files:
        return jsonify({"error": "No file part in the request"}), 400

    file = request.files["file"]
    if not file.filename:
        return jsonify({"error": "No file selected"}), 400

    annotation: str = request.form.get("annotation", "").strip()

    # Measure file size without loading everything into memory
    file.seek(0, 2)
    file_size: int = file.tell()
    file.seek(0)

    if file_size > _MAX_UPLOAD_BYTES:
        return jsonify({"error": "File exceeds 500 MB limit"}), 413

    content_type: str = file.content_type or "application/octet-stream"

    # 1. Write to S3 under the user's prefix
    upload_result = s3_service.upload_file(
        user_id=g.user_id,
        file_obj=file,
        filename=file.filename,
        content_type=content_type,
    )

    # 2. Persist metadata to DynamoDB
    record = dynamodb_service.create_file_record(
        user_id=g.user_id,
        file_id=upload_result["file_id"],
        filename=upload_result["filename"],
        s3_path=upload_result["s3_path"],
        s3_key=upload_result["s3_key"],
        file_size=file_size,
        content_type=content_type,
        annotation=annotation,
    )

    return jsonify({"message": "File uploaded successfully", "file": record}), 201


# ---------------------------------------------------------------------------
# Download (presigned URL)
# ---------------------------------------------------------------------------

@files_bp.route("/<file_id>/download", methods=["GET"])
@require_auth
def download_file(file_id: str):
    record = dynamodb_service.get_file(g.user_id, file_id)
    if not record:
        return jsonify({"error": "File not found"}), 404

    url = s3_service.generate_presigned_download_url(
        s3_key=record["s3Key"],
        filename=record["fileName"],
    )
    return jsonify({"download_url": url})


# ---------------------------------------------------------------------------
# Update annotation
# ---------------------------------------------------------------------------

@files_bp.route("/<file_id>/annotation", methods=["PUT"])
@require_auth
def update_annotation(file_id: str):
    body = request.get_json(silent=True) or {}
    if "annotation" not in body:
        return jsonify({"error": "'annotation' field is required"}), 400

    record = dynamodb_service.get_file(g.user_id, file_id)
    if not record:
        return jsonify({"error": "File not found"}), 404

    updated = dynamodb_service.update_annotation(
        user_id=g.user_id,
        file_id=file_id,
        annotation=str(body["annotation"]),
    )
    return jsonify({"file": updated})


# ---------------------------------------------------------------------------
# Delete
# ---------------------------------------------------------------------------

@files_bp.route("/<file_id>", methods=["DELETE"])
@require_auth
def delete_file(file_id: str):
    record = dynamodb_service.get_file(g.user_id, file_id)
    if not record:
        return jsonify({"error": "File not found"}), 404

    # Delete from S3 first; if it fails, we leave the DynamoDB record intact
    s3_service.delete_file(record["s3Key"])
    dynamodb_service.delete_file_record(g.user_id, file_id)

    return jsonify({"message": "File deleted successfully"})
