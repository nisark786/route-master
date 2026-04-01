# S3 Image Optimizer Lambda

This Lambda optimizes product and shop images after they land in S3.

It is triggered by S3 `ObjectCreated:*` events on:

- `media/products/`
- `media/shops/`

What it does:

- validates supported image content types
- auto-rotates from EXIF orientation
- resizes large images down to `MAX_DIMENSION`
- compresses and overwrites the same S3 object
- marks the object with `x-amz-meta-optimized=true` to avoid recursive processing loops

## Files

- `handler.py`
  - Lambda entrypoint
- `package.ps1`
  - builds a Lambda-compatible zip package with Docker
- `deploy.ps1`
  - deploys the Lambda from Docker using your repo `.env`
- `deploy.py`
  - creates/updates the IAM role, Lambda function, and S3 bucket notifications
- `iam-policy.json`
  - IAM permissions the deployment user needs to attach before running `deploy.py`

## Environment Variables

These should already exist in the repo root `.env` and `core_services/.env`:

```env
AWS_STORAGE_BUCKET_NAME=nisar-route-master-123
AWS_S3_REGION_NAME=ap-south-1
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
```

Optional Lambda tuning:

```env
MAX_DIMENSION=1600
JPEG_QUALITY=82
WEBP_QUALITY=80
PNG_MAX_COLORS=256
LAMBDA_TIMEOUT=30
LAMBDA_MEMORY_MB=512
LAMBDA_FUNCTION_NAME=route-management-image-optimizer
LAMBDA_ROLE_NAME=route-management-image-optimizer-role
```

## Deploy Steps

1. Attach `iam-policy.json` to the deployment IAM user.
2. Build the deployment zip:

```powershell
cd infra/aws/lambda/image_optimizer
.\package.ps1
```

3. Deploy the function and S3 triggers:

```powershell
.\deploy.ps1
```

## IAM Permissions Needed By The Lambda Execution Role

The deployment script creates an execution role with:

- `logs:CreateLogGroup`
- `logs:CreateLogStream`
- `logs:PutLogEvents`
- `s3:GetObject`
- `s3:PutObject`
- `s3:HeadObject`

on:

- `arn:aws:s3:::nisar-route-master-123/media/products/*`
- `arn:aws:s3:::nisar-route-master-123/media/shops/*`
