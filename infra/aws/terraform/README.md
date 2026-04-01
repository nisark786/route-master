# Terraform AWS Infra (Route Management)

This stack starts your migration from custom AWS scripts to Terraform.

Current scope:

- Image optimizer Lambda
- Lambda IAM role + inline policy
- Lambda invoke permission for S3
- Optional S3 bucket notification for:
  - `media/products/`
  - `media/shops/`
- Optional CloudFront + OAC for media reads
- Optional CloudFront read bucket policy

## Why this is staged

Your project already has live resources and custom scripts.  
This Terraform setup is intentionally safe-first so we do not accidentally overwrite:

- existing S3 bucket notifications
- existing S3 bucket policies

Both are controlled by explicit toggles.

## Prerequisites

1. Terraform `>= 1.5`
2. AWS credentials configured (`aws configure` or env vars)
3. Lambda zip built first:

```powershell
cd infra/aws/lambda/image_optimizer
.\package.ps1
```

## Configure

```powershell
cd infra/aws/terraform
Copy-Item terraform.tfvars.example terraform.tfvars
```

Edit `terraform.tfvars` as needed.

## First run (safe mode)

Keep these as `false` initially:

- `manage_bucket_notifications = false`
- `enable_cloudfront = false`
- `manage_cloudfront_bucket_policy = false`

Then run:

```powershell
terraform init
terraform plan
terraform apply
```

## Import existing live resources (recommended)

If resources already exist from your Python scripts, import them before apply:

```powershell
terraform import aws_iam_role.image_optimizer route-management-image-optimizer-role
terraform import aws_lambda_function.image_optimizer route-management-image-optimizer
terraform import aws_lambda_permission.allow_s3_invoke route-management-image-optimizer/AllowExecutionFromS3Bucket
```

Notes:

- `aws_lambda_permission` import id format is `function_name/statement_id`.
- If resource names differ, use your actual values from AWS.

## Enable S3 event triggers via Terraform

After confirming your bucket notification setup is owned by this project, set:

```hcl
manage_bucket_notifications = true
```

Then:

```powershell
terraform plan
terraform apply
```

Important: `aws_s3_bucket_notification` manages full notification config for the bucket.  
If other systems also write notifications, coordinate first.

## Enable CloudFront via Terraform

Set:

```hcl
enable_cloudfront = true
```

Optionally let Terraform also manage bucket policy:

```hcl
manage_cloudfront_bucket_policy = true
```

Then apply and use output:

- `cloudfront_domain_name`

Set in app env:

```env
AWS_S3_CUSTOM_DOMAIN=<cloudfront_domain_name>
```

## Next migration targets

After this stack is stable, we can migrate the rest in phases:

1. VPC + subnets + security groups
2. ECR repos
3. EKS cluster + node groups
4. IAM roles for service accounts
5. Route53 + ACM + ingress DNS
6. Monitoring stack add-ons
