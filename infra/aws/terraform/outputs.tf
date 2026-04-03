output "lambda_function_name" {
  description = "Image optimizer Lambda function name."
  value       = try(aws_lambda_function.image_optimizer[0].function_name, null)
}

output "lambda_function_arn" {
  description = "Image optimizer Lambda function ARN."
  value       = try(aws_lambda_function.image_optimizer[0].arn, null)
}

output "lambda_role_arn" {
  description = "IAM role ARN used by image optimizer Lambda."
  value       = try(aws_iam_role.image_optimizer[0].arn, null)
}

output "cloudfront_domain_name" {
  description = "CloudFront domain for media reads when enabled."
  value       = var.enable_cloudfront ? aws_cloudfront_distribution.media[0].domain_name : null
}

output "cloudfront_distribution_id" {
  description = "CloudFront distribution ID when enabled."
  value       = var.enable_cloudfront ? aws_cloudfront_distribution.media[0].id : null
}

output "managed_data_security_group_id" {
  description = "Security group ID for managed data layer resources."
  value       = local.managed_data_enabled ? aws_security_group.managed_data[0].id : null
}

output "rds_endpoint" {
  description = "RDS PostgreSQL endpoint when managed data layer is enabled."
  value       = try(aws_db_instance.managed_postgres[0].address, null)
}

output "rds_port" {
  description = "RDS PostgreSQL port."
  value       = try(aws_db_instance.managed_postgres[0].port, null)
}

output "rds_core_db_name" {
  description = "RDS core database name."
  value       = local.managed_data_enabled ? var.rds_core_db_name : null
}

output "rds_ai_db_name" {
  description = "RDS AI database name (create during cutover migration)."
  value       = local.managed_data_enabled ? var.rds_ai_db_name : null
}

output "documentdb_endpoint" {
  description = "DocumentDB endpoint when managed data layer is enabled."
  value       = try(aws_docdb_cluster.managed[0].endpoint, null)
}

output "documentdb_port" {
  description = "DocumentDB port."
  value       = local.managed_data_enabled ? var.docdb_port : null
}

output "amazon_mq_endpoint" {
  description = "Amazon MQ RabbitMQ endpoint when managed data layer is enabled."
  value       = try(aws_mq_broker.managed[0].instances[0].endpoints[0], null)
}

output "managed_data_secret_arn" {
  description = "Secrets Manager ARN containing managed data endpoints and credentials."
  value       = local.managed_data_enabled ? aws_secretsmanager_secret.managed_data[0].arn : null
}

output "elasticache_redis_endpoint" {
  description = "ElastiCache Redis primary endpoint when managed Redis is enabled."
  value       = try(aws_elasticache_replication_group.managed[0].primary_endpoint_address, null)
}

output "elasticache_redis_port" {
  description = "ElastiCache Redis port."
  value       = local.managed_data_enabled && var.enable_managed_redis ? var.redis_port : null
}
