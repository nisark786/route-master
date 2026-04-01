variable "aws_region" {
  description = "AWS region for resources."
  type        = string
  default     = "ap-south-1"
}

variable "bucket_name" {
  description = "Existing S3 bucket that stores media objects."
  type        = string
  default     = "nisar-route-master-123"
}

variable "lambda_function_name" {
  description = "Image optimizer Lambda function name."
  type        = string
  default     = "route-management-image-optimizer"
}

variable "lambda_role_name" {
  description = "IAM role name used by image optimizer Lambda."
  type        = string
  default     = "route-management-image-optimizer-role"
}

variable "lambda_runtime" {
  description = "Lambda runtime."
  type        = string
  default     = "python3.12"
}

variable "lambda_handler" {
  description = "Lambda handler entrypoint."
  type        = string
  default     = "handler.lambda_handler"
}

variable "lambda_timeout" {
  description = "Lambda timeout in seconds."
  type        = number
  default     = 30
}

variable "lambda_memory_mb" {
  description = "Lambda memory in MB."
  type        = number
  default     = 512
}

variable "lambda_architectures" {
  description = "Lambda CPU architecture."
  type        = list(string)
  default     = ["x86_64"]
}

variable "lambda_package_path" {
  description = "Path to the prebuilt image optimizer zip package."
  type        = string
  default     = "../lambda/image_optimizer/build/image-optimizer.zip"
}

variable "max_dimension" {
  description = "Maximum dimension used by optimizer."
  type        = string
  default     = "1600"
}

variable "jpeg_quality" {
  description = "JPEG quality used by optimizer."
  type        = string
  default     = "82"
}

variable "webp_quality" {
  description = "WEBP quality used by optimizer."
  type        = string
  default     = "80"
}

variable "png_max_colors" {
  description = "PNG quantize max color count."
  type        = string
  default     = "256"
}

variable "manage_bucket_notifications" {
  description = "When true, Terraform manages S3 bucket notifications for media prefixes. Enable only when this stack should own bucket notifications."
  type        = bool
  default     = false
}

variable "enable_cloudfront" {
  description = "When true, create CloudFront distribution and OAC for media reads."
  type        = bool
  default     = false
}

variable "cloudfront_price_class" {
  description = "CloudFront distribution price class."
  type        = string
  default     = "PriceClass_200"
}

variable "cloudfront_comment" {
  description = "CloudFront distribution comment."
  type        = string
  default     = "RouteMaster media CDN"
}

variable "manage_cloudfront_bucket_policy" {
  description = "When true and CloudFront is enabled, Terraform sets the S3 bucket policy for CloudFront OAC reads on /media/*."
  type        = bool
  default     = false
}
