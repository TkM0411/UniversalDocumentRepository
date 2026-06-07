"""
Health check route.

GET /health
-----------
Probes each downstream dependency and returns a structured report.

Response shape
--------------
{
  "status": "healthy" | "degraded",
  "checks": {
    "dynamodb": { "status": "ok" | "error", "detail": "..." },
    "s3":       { "status": "ok" | "error", "detail": "..." }
  }
}

HTTP status
-----------
  200  – all checks passed
  503  – one or more checks failed

Used by the ALB target-group health check, container orchestrators (ECS /
Kubernetes liveness probes), and monitoring tools. Does NOT require auth.
"""

import time

import boto3
from botocore.exceptions import BotoCoreError, ClientError
from flask import Blueprint, jsonify

from config import Config

health_bp = Blueprint("health", __name__)

# Reuse module-level clients (boto3 clients are thread-safe)
_dynamodb = boto3.client("dynamodb", region_name=Config.AWS_REGION)
_s3 = boto3.client("s3", region_name=Config.AWS_REGION)


def _check_dynamodb() -> dict:
    """Verify the FileMetadata table exists and is ACTIVE."""
    t0 = time.monotonic()
    try:
        resp = _dynamodb.describe_table(TableName=Config.DYNAMODB_TABLE_NAME)
        table_status = resp["Table"]["TableStatus"]
        elapsed_ms = round((time.monotonic() - t0) * 1000)
        if table_status == "ACTIVE":
            return {"status": "ok", "latency_ms": elapsed_ms}
        return {
            "status": "error",
            "detail": f"Table status is '{table_status}', expected ACTIVE",
            "latency_ms": elapsed_ms,
        }
    except ClientError as exc:
        code = exc.response["Error"]["Code"]
        return {"status": "error", "detail": f"ClientError: {code}"}
    except BotoCoreError as exc:
        return {"status": "error", "detail": str(exc)}


def _check_s3() -> dict:
    """Verify the UniversalDocumentRepository bucket is accessible."""
    t0 = time.monotonic()
    try:
        _s3.head_bucket(Bucket=Config.S3_BUCKET_NAME)
        elapsed_ms = round((time.monotonic() - t0) * 1000)
        return {"status": "ok", "latency_ms": elapsed_ms}
    except ClientError as exc:
        code = exc.response["Error"]["Code"]
        # 301 means the bucket exists but in a different region – still reachable
        if code in ("301", "200"):
            elapsed_ms = round((time.monotonic() - t0) * 1000)
            return {"status": "ok", "latency_ms": elapsed_ms}
        return {"status": "error", "detail": f"ClientError: {code}"}
    except BotoCoreError as exc:
        return {"status": "error", "detail": str(exc)}


@health_bp.route("/health", methods=["GET"])
def health():
    checks = {
        "dynamodb": _check_dynamodb(),
        "s3": _check_s3(),
    }

    all_ok = all(c["status"] == "ok" for c in checks.values())
    overall = "healthy" if all_ok else "degraded"
    http_status = 200 if all_ok else 503

    return jsonify({"status": overall, "checks": checks}), http_status
