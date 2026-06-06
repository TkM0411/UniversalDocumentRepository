import os


class Config:
    # ------------------------------------------------------------------ #
    # AWS General
    # ------------------------------------------------------------------ #
    AWS_REGION: str = os.environ.get("AWS_REGION", "us-east-1")

    # ------------------------------------------------------------------ #
    # S3
    # ------------------------------------------------------------------ #
    S3_BUCKET_NAME: str = os.environ.get("S3_BUCKET_NAME", "UniversalDocumentRepository")

    # ------------------------------------------------------------------ #
    # DynamoDB
    # ------------------------------------------------------------------ #
    DYNAMODB_TABLE_NAME: str = os.environ.get("DYNAMODB_TABLE_NAME", "FileMetadata")

    # ------------------------------------------------------------------ #
    # Cognito
    # ------------------------------------------------------------------ #
    # e.g. us-east-1_AbCdEfGhI
    COGNITO_USER_POOL_ID: str = os.environ.get("COGNITO_USER_POOL_ID", "")
    # App client ID (public client, no secret)
    COGNITO_CLIENT_ID: str = os.environ.get("COGNITO_CLIENT_ID", "")
    COGNITO_REGION: str = os.environ.get("COGNITO_REGION", AWS_REGION)

    @classmethod
    def cognito_issuer(cls) -> str:
        return (
            f"https://cognito-idp.{cls.COGNITO_REGION}.amazonaws.com"
            f"/{cls.COGNITO_USER_POOL_ID}"
        )

    @classmethod
    def jwks_url(cls) -> str:
        return f"{cls.cognito_issuer()}/.well-known/jwks.json"

    # ------------------------------------------------------------------ #
    # CORS
    # ------------------------------------------------------------------ #
    # Comma-separated list of allowed origins, e.g. https://d1234.cloudfront.net
    ALLOWED_ORIGINS: list[str] = os.environ.get("ALLOWED_ORIGINS", "*").split(",")
