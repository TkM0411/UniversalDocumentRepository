/**
 * config.js
 *
 * ⚠️  Values below must be filled in by the DevOps team before deployment.
 *     Replace every placeholder with the actual AWS resource values.
 *
 * How to deploy:
 *   1. Fill in the values below.
 *   2. Upload all frontend/ files to the S3 static-hosting bucket.
 *   3. Invalidate the CloudFront distribution cache.
 */

const CONFIG = Object.freeze({
  // ------------------------------------------------------------------
  // Cognito
  // ------------------------------------------------------------------

  /** Cognito Hosted UI domain (without https://)
   *  e.g. "my-app.auth.us-east-1.amazoncognito.com"
   */
  COGNITO_DOMAIN: "REPLACE_WITH_COGNITO_DOMAIN",

  /** App Client ID (public client – no client secret) */
  COGNITO_CLIENT_ID: "REPLACE_WITH_COGNITO_CLIENT_ID",

  /** OAuth2 scopes to request */
  COGNITO_SCOPE: "openid email profile",

  /** The URL Cognito will redirect to after login/signup.
   *  Must match an "Allowed callback URL" in the App Client settings.
   *  e.g. "https://d1234abcd.cloudfront.net/callback.html"
   */
  COGNITO_REDIRECT_URI: "REPLACE_WITH_CLOUDFRONT_URL/callback.html",

  /** The URL Cognito redirects to after logout.
   *  Must match an "Allowed sign-out URL" in the App Client settings.
   *  e.g. "https://d1234abcd.cloudfront.net/index.html"
   */
  COGNITO_LOGOUT_URI: "REPLACE_WITH_CLOUDFRONT_URL/index.html",

  // ------------------------------------------------------------------
  // Backend API
  // ------------------------------------------------------------------

  /** Base URL of the Python container (behind ALB / API Gateway).
   *  No trailing slash.
   *  e.g. "https://api.my-app.example.com"  or  "https://xxxx.execute-api.us-east-1.amazonaws.com/prod"
   */
  API_BASE_URL: "REPLACE_WITH_BACKEND_API_URL",
});
