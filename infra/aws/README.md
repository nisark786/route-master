# AWS Media Pipeline

This folder contains the next-stage AWS pieces for media delivery and processing:

- `lambda/image_optimizer/`
  - S3-triggered image validation + compression Lambda
- `cloudfront/`
  - app-facing setup notes for serving `media/` through CloudFront
- `terraform/`
  - Terraform-managed AWS resources (starting with image optimizer + optional CloudFront)

Recommended rollout order:

1. Keep current signed S3 URLs working
2. Create CloudFront distribution in front of the S3 bucket
3. Set `AWS_S3_CUSTOM_DOMAIN` to the CloudFront domain
4. Deploy the image optimizer Lambda and attach it to S3 `ObjectCreated` events

Terraform-first path:

1. Build image optimizer package (`lambda/image_optimizer/package.ps1`)
2. Apply `terraform/` stack in safe mode
3. Import existing resources into Terraform state
4. Enable notification/bucket-policy toggles only after validation
