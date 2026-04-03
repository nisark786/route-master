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

variable "enable_image_optimizer_stack" {
  description = "When true, manage image optimizer Lambda/IAM/S3 notification resources."
  type        = bool
  default     = true
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

variable "enable_managed_data_layer" {
  description = "When true, provision managed data services (RDS, DocumentDB, Amazon MQ) for EKS offload."
  type        = bool
  default     = false
}

variable "enable_managed_rds" {
  description = "When true, provision managed RDS PostgreSQL."
  type        = bool
  default     = true
}

variable "enable_managed_docdb" {
  description = "When true, provision managed DocumentDB."
  type        = bool
  default     = true
}

variable "enable_managed_mq" {
  description = "When true, provision managed Amazon MQ (RabbitMQ)."
  type        = bool
  default     = true
}

variable "enable_managed_redis" {
  description = "When true, provision managed ElastiCache Redis."
  type        = bool
  default     = false
}

variable "eks_cluster_name" {
  description = "Existing EKS cluster name used to derive VPC and security context for managed data resources."
  type        = string
  default     = ""
}

variable "managed_data_subnet_ids" {
  description = "Optional subnet IDs for managed data resources. If empty, EKS cluster subnets are used."
  type        = list(string)
  default     = []
}

variable "rds_identifier" {
  description = "RDS PostgreSQL instance identifier."
  type        = string
  default     = "route-management-postgres"
}

variable "rds_instance_class" {
  description = "RDS PostgreSQL instance class."
  type        = string
  default     = "db.t3.micro"
}

variable "rds_engine_version" {
  description = "RDS PostgreSQL engine version. Leave empty to let AWS choose a supported default."
  type        = string
  default     = ""
}

variable "rds_allocated_storage" {
  description = "RDS initial allocated storage (GiB)."
  type        = number
  default     = 20
}

variable "rds_max_allocated_storage" {
  description = "RDS max autoscaled storage (GiB)."
  type        = number
  default     = 100
}

variable "rds_port" {
  description = "RDS PostgreSQL port."
  type        = number
  default     = 5432
}

variable "rds_core_db_name" {
  description = "Primary database created at RDS provision time (core DB)."
  type        = string
  default     = "route_core_db"
}

variable "rds_ai_db_name" {
  description = "Logical AI database name to create during cutover migration."
  type        = string
  default     = "route_ai_db"
}

variable "rds_master_username" {
  description = "RDS master username."
  type        = string
  default     = "route_admin"
}

variable "rds_master_password" {
  description = "Optional RDS master password. Leave empty to auto-generate."
  type        = string
  default     = ""
  sensitive   = true
}

variable "rds_backup_retention_days" {
  description = "RDS backup retention days."
  type        = number
  default     = 7
}

variable "rds_deletion_protection" {
  description = "Enable deletion protection for RDS."
  type        = bool
  default     = false
}

variable "rds_skip_final_snapshot" {
  description = "Skip final snapshot on RDS destroy."
  type        = bool
  default     = true
}

variable "docdb_cluster_identifier" {
  description = "DocumentDB cluster identifier."
  type        = string
  default     = "route-management-docdb"
}

variable "docdb_instance_class" {
  description = "DocumentDB instance class."
  type        = string
  default     = "db.t3.medium"
}

variable "docdb_instance_count" {
  description = "Number of DocumentDB instances."
  type        = number
  default     = 1
}

variable "docdb_engine_version" {
  description = "DocumentDB engine version."
  type        = string
  default     = "5.0.0"
}

variable "docdb_master_username" {
  description = "DocumentDB master username."
  type        = string
  default     = "route_docdb_admin"
}

variable "docdb_master_password" {
  description = "Optional DocumentDB master password. Leave empty to auto-generate."
  type        = string
  default     = ""
  sensitive   = true
}

variable "docdb_port" {
  description = "DocumentDB port."
  type        = number
  default     = 27017
}

variable "docdb_skip_final_snapshot" {
  description = "Skip final snapshot on DocumentDB destroy."
  type        = bool
  default     = true
}

variable "mq_broker_name" {
  description = "Amazon MQ broker name."
  type        = string
  default     = "route-management-rabbitmq"
}

variable "mq_engine_version" {
  description = "Amazon MQ RabbitMQ engine version."
  type        = string
  default     = "3.13"
}

variable "mq_instance_type" {
  description = "Amazon MQ instance type."
  type        = string
  default     = "mq.t3.micro"
}

variable "mq_username" {
  description = "Amazon MQ username."
  type        = string
  default     = "route_user_prod"
}

variable "mq_password" {
  description = "Optional Amazon MQ password. Leave empty to auto-generate."
  type        = string
  default     = ""
  sensitive   = true
}

variable "redis_replication_group_id" {
  description = "ElastiCache Redis replication group ID."
  type        = string
  default     = "route-management-redis"
}

variable "redis_node_type" {
  description = "ElastiCache Redis node type."
  type        = string
  default     = "cache.t4g.micro"
}

variable "redis_engine_version" {
  description = "ElastiCache Redis engine version."
  type        = string
  default     = "7.0"
}

variable "redis_port" {
  description = "ElastiCache Redis port."
  type        = number
  default     = 6379
}

variable "redis_num_cache_clusters" {
  description = "Number of cache clusters for ElastiCache Redis (single-AZ uses 1)."
  type        = number
  default     = 1
}
