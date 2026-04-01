# CloudFront Setup

Current application support:

- Django already supports `AWS_S3_CUSTOM_DOMAIN`
- when set, media URLs will be generated with that host instead of the raw S3 domain

Set these environment variables after creating the distribution:

```env
AWS_S3_CUSTOM_DOMAIN=your-distribution-id.cloudfront.net
USE_S3_MEDIA=True
AWS_STORAGE_BUCKET_NAME=nisar-route-master-123
AWS_S3_REGION_NAME=ap-south-1
```

Recommended AWS setup:

1. Create a CloudFront distribution with the S3 bucket as origin
2. Use Origin Access Control so the bucket stays private
3. Cache `/media/products/*` and `/media/shops/*`
4. Allow `GET`, `HEAD`, `OPTIONS`
5. If you want browser uploads to continue directly to S3, keep S3 CORS enabled for `PUT`

Notes:

- The current app still uploads directly to S3 using presigned S3 URLs
- CloudFront is used for reading images, not uploading them
- If you later want signed CloudFront URLs instead of signed S3 URLs, add a CloudFront signer layer in Django

Automation:

- Use [create_distribution.py](C:/nisar/Route_management/infra/aws/cloudfront/create_distribution.py) after attaching the IAM permissions in [iam-policy.json](C:/nisar/Route_management/infra/aws/cloudfront/iam-policy.json)

Example run:

```powershell
docker compose exec -T backend python /app/../infra/aws/cloudfront/create_distribution.py
```

If your backend container does not include the repo root path, run the script from the host Python with the same AWS env vars loaded.
