# Universal Document Repository
A vibe-coded web application to store files on the cloud and allow the user to add text annotations about the file.

## Functionalities
- Upload your personal documents and annotate them with verbose descriptions.
- Uploaded files securely stored on cloud.
- Download your uploaded files on-demand.

## Tech Stack
### Front-End:
- HTML
- CSS
- JavaScript
### Back-End:
- Python
- Flask
- Amazon API Gateway
### Data Storage:
- AWS DynamoDB
### User File Storage
- AWS S3 Bucket
### Containerization Tools
- Docker Compose for Development Environment
- AWS EKS for Hosting Backend API
### Authentication & Authorization
- Amazon Cognito
### Infrastructure As Code (IAC)
- HashiCorp Terraform
### CI/CD Pipelines
- GitHub Actions

## AWS Infrastructure Components
This project leverages the following AWS Infrastructure Components:
### S3 Buckets
- To hold source code files for the front-end.
- To store user uploaded files.
### Amazon Cognito User Pool
- For authentication
### Amazon EKS
- For running backend containers
### Amazon API Gateway
- For exposing API
### Application Load Balancer
- To load balance and communicate with the backend service
### DynamoDB
 - For data storage
### AWS CloudFront
- CDN for caching and serving front-end.
