"""
Flask application factory.

Environment variables required at runtime:
  AWS_REGION              – AWS region (default: us-east-1)
  S3_BUCKET_NAME          – S3 bucket for user files (default: UniversalDocumentRepository)
  DYNAMODB_TABLE_NAME     – DynamoDB table name (default: FileMetadata)
  COGNITO_USER_POOL_ID    – Cognito User Pool ID, e.g. us-east-1_AbCdEfGhI
  COGNITO_CLIENT_ID       – Cognito App Client ID (public client, no secret)
  COGNITO_REGION          – Cognito region (defaults to AWS_REGION)
  ALLOWED_ORIGINS         – Comma-separated CORS origins, e.g. https://d123.cloudfront.net
"""

from flask import Flask, jsonify  # jsonify retained for error handlers below
from flask_cors import CORS

from config import Config
from routes.files import files_bp
from routes.health import health_bp
from routes.users import users_bp


def create_app() -> Flask:
    app = Flask(__name__)

    # ------------------------------------------------------------------
    # CORS – restrict to the CloudFront distribution in production
    # ------------------------------------------------------------------
    CORS(
        app,
        origins=Config.ALLOWED_ORIGINS,
        allow_headers=["Authorization", "Content-Type"],
        methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        supports_credentials=False,
    )

    # ------------------------------------------------------------------
    # Blueprints
    # ------------------------------------------------------------------
    app.register_blueprint(files_bp, url_prefix="/api/files")
    app.register_blueprint(users_bp, url_prefix="/api/users")
    app.register_blueprint(health_bp)   # mounts at /health (no prefix)

    # ------------------------------------------------------------------
    # Global error handlers
    # ------------------------------------------------------------------
    @app.errorhandler(404)
    def not_found(e):
        return jsonify({"error": "Not found"}), 404

    @app.errorhandler(405)
    def method_not_allowed(e):
        return jsonify({"error": "Method not allowed"}), 405

    @app.errorhandler(Exception)
    def unhandled_exception(e):
        app.logger.exception("Unhandled exception: %s", e)
        return jsonify({"error": "Internal server error"}), 500

    return app


if __name__ == "__main__":
    application = create_app()
    application.run(host="0.0.0.0", port=5000, debug=False)
