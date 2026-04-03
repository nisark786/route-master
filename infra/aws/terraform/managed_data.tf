locals {
  managed_data_enabled = var.enable_managed_data_layer && var.eks_cluster_name != ""
  rds_enabled          = local.managed_data_enabled && var.enable_managed_rds
  docdb_enabled        = local.managed_data_enabled && var.enable_managed_docdb
  mq_enabled           = local.managed_data_enabled && var.enable_managed_mq
  redis_enabled        = local.managed_data_enabled && var.enable_managed_redis
}

data "aws_eks_cluster" "target" {
  count = local.managed_data_enabled ? 1 : 0
  name  = var.eks_cluster_name
}

locals {
  managed_vpc_id            = try(data.aws_eks_cluster.target[0].vpc_config[0].vpc_id, null)
  managed_cluster_sg_id     = try(data.aws_eks_cluster.target[0].vpc_config[0].cluster_security_group_id, null)
  managed_effective_subnets = length(var.managed_data_subnet_ids) > 0 ? var.managed_data_subnet_ids : try(data.aws_eks_cluster.target[0].vpc_config[0].subnet_ids, [])
}

resource "aws_security_group" "managed_data" {
  count       = local.managed_data_enabled ? 1 : 0
  name        = "${var.eks_cluster_name}-managed-data-sg"
  description = "Managed data layer access for ${var.eks_cluster_name}"
  vpc_id      = local.managed_vpc_id

  ingress {
    description     = "PostgreSQL from EKS cluster SG"
    from_port       = var.rds_port
    to_port         = var.rds_port
    protocol        = "tcp"
    security_groups = [local.managed_cluster_sg_id]
  }

  dynamic "ingress" {
    for_each = local.docdb_enabled ? [1] : []
    content {
      description     = "DocumentDB from EKS cluster SG"
      from_port       = var.docdb_port
      to_port         = var.docdb_port
      protocol        = "tcp"
      security_groups = [local.managed_cluster_sg_id]
    }
  }

  dynamic "ingress" {
    for_each = local.mq_enabled ? [1] : []
    content {
      description     = "RabbitMQ AMQP over TLS from EKS cluster SG"
      from_port       = 5671
      to_port         = 5671
      protocol        = "tcp"
      security_groups = [local.managed_cluster_sg_id]
    }
  }

  dynamic "ingress" {
    for_each = local.mq_enabled ? [1] : []
    content {
      description     = "RabbitMQ AMQP from EKS cluster SG"
      from_port       = 5672
      to_port         = 5672
      protocol        = "tcp"
      security_groups = [local.managed_cluster_sg_id]
    }
  }

  dynamic "ingress" {
    for_each = local.redis_enabled ? [1] : []
    content {
      description     = "Redis from EKS cluster SG"
      from_port       = var.redis_port
      to_port         = var.redis_port
      protocol        = "tcp"
      security_groups = [local.managed_cluster_sg_id]
    }
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_db_subnet_group" "managed" {
  count      = local.rds_enabled ? 1 : 0
  name       = "${var.eks_cluster_name}-managed-rds-subnets"
  subnet_ids = local.managed_effective_subnets
}

resource "random_password" "rds_master" {
  count   = local.rds_enabled && var.rds_master_password == "" ? 1 : 0
  length  = 32
  special = true
  # RDS master password restrictions: exclude / @ " and space
  override_special = "!#$%&*()-_=+[]{}:;,.?"
}

locals {
  rds_master_password_effective = var.rds_master_password != "" ? var.rds_master_password : try(random_password.rds_master[0].result, null)
}

resource "aws_db_instance" "managed_postgres" {
  count                      = local.rds_enabled ? 1 : 0
  identifier                 = var.rds_identifier
  engine                     = "postgres"
  engine_version             = var.rds_engine_version != "" ? var.rds_engine_version : null
  instance_class             = var.rds_instance_class
  allocated_storage          = var.rds_allocated_storage
  max_allocated_storage      = var.rds_max_allocated_storage
  storage_encrypted          = true
  db_name                    = var.rds_core_db_name
  username                   = var.rds_master_username
  password                   = local.rds_master_password_effective
  port                       = var.rds_port
  backup_retention_period    = var.rds_backup_retention_days
  deletion_protection        = var.rds_deletion_protection
  skip_final_snapshot        = var.rds_skip_final_snapshot
  apply_immediately          = true
  publicly_accessible        = false
  db_subnet_group_name       = aws_db_subnet_group.managed[0].name
  vpc_security_group_ids     = [aws_security_group.managed_data[0].id]
  auto_minor_version_upgrade = true
}

resource "aws_docdb_subnet_group" "managed" {
  count      = local.docdb_enabled ? 1 : 0
  name       = "${var.eks_cluster_name}-managed-docdb-subnets"
  subnet_ids = local.managed_effective_subnets
}

resource "random_password" "docdb_master" {
  count   = local.docdb_enabled && var.docdb_master_password == "" ? 1 : 0
  length  = 32
  special = true
}

locals {
  docdb_master_password_effective = var.docdb_master_password != "" ? var.docdb_master_password : try(random_password.docdb_master[0].result, null)
}

resource "aws_docdb_cluster" "managed" {
  count                  = local.docdb_enabled ? 1 : 0
  cluster_identifier     = var.docdb_cluster_identifier
  engine                 = "docdb"
  engine_version         = var.docdb_engine_version
  master_username        = var.docdb_master_username
  master_password        = local.docdb_master_password_effective
  storage_encrypted      = true
  db_subnet_group_name   = aws_docdb_subnet_group.managed[0].name
  vpc_security_group_ids = [aws_security_group.managed_data[0].id]
  skip_final_snapshot    = var.docdb_skip_final_snapshot
  apply_immediately      = true
}

resource "aws_docdb_cluster_instance" "managed" {
  count              = local.docdb_enabled ? var.docdb_instance_count : 0
  identifier         = "${var.docdb_cluster_identifier}-${count.index + 1}"
  cluster_identifier = aws_docdb_cluster.managed[0].id
  instance_class     = var.docdb_instance_class
}

resource "random_password" "mq_password" {
  count   = local.mq_enabled && var.mq_password == "" ? 1 : 0
  length  = 32
  special = true
}

locals {
  mq_password_effective = var.mq_password != "" ? var.mq_password : try(random_password.mq_password[0].result, null)
}

resource "aws_mq_broker" "managed" {
  count                      = local.mq_enabled ? 1 : 0
  broker_name                = var.mq_broker_name
  engine_type                = "RabbitMQ"
  engine_version             = var.mq_engine_version
  host_instance_type         = var.mq_instance_type
  deployment_mode            = "SINGLE_INSTANCE"
  publicly_accessible        = false
  auto_minor_version_upgrade = true
  subnet_ids                 = [local.managed_effective_subnets[0]]
  security_groups            = [aws_security_group.managed_data[0].id]

  user {
    username = var.mq_username
    password = local.mq_password_effective
  }

  logs {
    general = true
  }
}

resource "aws_elasticache_subnet_group" "managed" {
  count       = local.redis_enabled ? 1 : 0
  name        = "${var.eks_cluster_name}-managed-redis-subnets"
  description = "Managed Redis subnet group for ${var.eks_cluster_name}"
  subnet_ids  = local.managed_effective_subnets
}

resource "aws_elasticache_replication_group" "managed" {
  count                        = local.redis_enabled ? 1 : 0
  replication_group_id         = var.redis_replication_group_id
  description                  = "Managed Redis for ${var.eks_cluster_name}"
  engine                       = "redis"
  engine_version               = var.redis_engine_version
  node_type                    = var.redis_node_type
  num_cache_clusters           = var.redis_num_cache_clusters
  port                         = var.redis_port
  subnet_group_name            = aws_elasticache_subnet_group.managed[0].name
  security_group_ids           = [aws_security_group.managed_data[0].id]
  at_rest_encryption_enabled   = true
  transit_encryption_enabled   = false
  automatic_failover_enabled   = false
  multi_az_enabled             = false
  auto_minor_version_upgrade   = true
  apply_immediately            = true
}

resource "aws_secretsmanager_secret" "managed_data" {
  count       = local.managed_data_enabled ? 1 : 0
  name        = "/route-management/${var.eks_cluster_name}/managed-data"
  description = "Managed data layer connection bundle for Route Management"
}

resource "aws_secretsmanager_secret_version" "managed_data" {
  count     = local.managed_data_enabled ? 1 : 0
  secret_id = aws_secretsmanager_secret.managed_data[0].id

  secret_string = jsonencode({
    rds = {
      host     = try(aws_db_instance.managed_postgres[0].address, null)
      port     = try(aws_db_instance.managed_postgres[0].port, null)
      db_core  = var.rds_core_db_name
      db_ai    = var.rds_ai_db_name
      user     = var.rds_master_username
      password = local.rds_master_password_effective
    }
    documentdb = {
      host     = try(aws_docdb_cluster.managed[0].endpoint, null)
      port     = var.docdb_port
      username = var.docdb_master_username
      password = local.docdb_master_password_effective
    }
    rabbitmq = {
      endpoint = try(aws_mq_broker.managed[0].instances[0].endpoints[0], null)
      username = var.mq_username
      password = local.mq_password_effective
    }
    redis = {
      host = try(aws_elasticache_replication_group.managed[0].primary_endpoint_address, null)
      port = var.redis_port
      url  = try(format("redis://%s:%d/2", aws_elasticache_replication_group.managed[0].primary_endpoint_address, var.redis_port), null)
    }
  })
}
