output "lambda_function_name" {
  description = "Image optimizer Lambda function name."
  value       = aws_lambda_function.image_optimizer.function_name
}

output "lambda_function_arn" {
  description = "Image optimizer Lambda function ARN."
  value       = aws_lambda_function.image_optimizer.arn
}

output "lambda_role_arn" {
  description = "IAM role ARN used by image optimizer Lambda."
  value       = aws_iam_role.image_optimizer.arn
}

output "cloudfront_domain_name" {
  description = "CloudFront domain for media reads when enabled."
  value       = var.enable_cloudfront ? aws_cloudfront_distribution.media[0].domain_name : null
}

output "cloudfront_distribution_id" {
  description = "CloudFront distribution ID when enabled."
  value       = var.enable_cloudfront ? aws_cloudfront_distribution.media[0].id : null
}
