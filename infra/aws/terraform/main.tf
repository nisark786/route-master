data "aws_caller_identity" "current" {}

data "aws_s3_bucket" "media" {
  bucket = var.bucket_name
}

data "aws_iam_policy_document" "lambda_assume_role" {
  statement {
    effect = "Allow"
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "image_optimizer" {
  name               = var.lambda_role_name
  assume_role_policy = data.aws_iam_policy_document.lambda_assume_role.json
}

data "aws_iam_policy_document" "image_optimizer_inline" {
  statement {
    sid    = "AllowCloudWatchLogs"
    effect = "Allow"
    actions = [
      "logs:CreateLogGroup",
      "logs:CreateLogStream",
      "logs:PutLogEvents",
    ]
    resources = ["arn:aws:logs:*:${data.aws_caller_identity.current.account_id}:*"]
  }

  statement {
    sid    = "AllowMediaObjectReadWrite"
    effect = "Allow"
    actions = [
      "s3:GetObject",
      "s3:PutObject",
      "s3:HeadObject",
    ]
    resources = [
      "arn:aws:s3:::${var.bucket_name}/media/products/*",
      "arn:aws:s3:::${var.bucket_name}/media/shops/*",
    ]
  }
}

resource "aws_iam_role_policy" "image_optimizer_inline" {
  name   = "${var.lambda_function_name}-inline"
  role   = aws_iam_role.image_optimizer.id
  policy = data.aws_iam_policy_document.image_optimizer_inline.json
}

resource "aws_lambda_function" "image_optimizer" {
  function_name = var.lambda_function_name
  role          = aws_iam_role.image_optimizer.arn
  runtime       = var.lambda_runtime
  handler       = var.lambda_handler
  timeout       = var.lambda_timeout
  memory_size   = var.lambda_memory_mb
  architectures = var.lambda_architectures
  filename      = var.lambda_package_path

  source_code_hash = filebase64sha256(var.lambda_package_path)

  environment {
    variables = {
      MAX_DIMENSION  = var.max_dimension
      JPEG_QUALITY   = var.jpeg_quality
      WEBP_QUALITY   = var.webp_quality
      PNG_MAX_COLORS = var.png_max_colors
    }
  }

  depends_on = [aws_iam_role_policy.image_optimizer_inline]
}

resource "aws_lambda_permission" "allow_s3_invoke" {
  statement_id   = "AllowExecutionFromS3Bucket"
  action         = "lambda:InvokeFunction"
  function_name  = aws_lambda_function.image_optimizer.function_name
  principal      = "s3.amazonaws.com"
  source_arn     = data.aws_s3_bucket.media.arn
  source_account = data.aws_caller_identity.current.account_id
}

resource "aws_s3_bucket_notification" "media_image_optimizer" {
  count  = var.manage_bucket_notifications ? 1 : 0
  bucket = data.aws_s3_bucket.media.id

  lambda_function {
    id                  = "route-management-products-image-optimizer"
    lambda_function_arn = aws_lambda_function.image_optimizer.arn
    events              = ["s3:ObjectCreated:*"]
    filter_prefix       = "media/products/"
  }

  lambda_function {
    id                  = "route-management-shops-image-optimizer"
    lambda_function_arn = aws_lambda_function.image_optimizer.arn
    events              = ["s3:ObjectCreated:*"]
    filter_prefix       = "media/shops/"
  }

  depends_on = [aws_lambda_permission.allow_s3_invoke]
}

resource "aws_cloudfront_origin_access_control" "media" {
  count                             = var.enable_cloudfront ? 1 : 0
  name                              = "${var.bucket_name}-media-oac"
  description                       = "OAC for ${var.bucket_name} media delivery"
  origin_access_control_origin_type = "s3"
  signing_behavior                  = "always"
  signing_protocol                  = "sigv4"
}

resource "aws_cloudfront_distribution" "media" {
  count = var.enable_cloudfront ? 1 : 0

  enabled     = true
  price_class = var.cloudfront_price_class
  comment     = var.cloudfront_comment

  origin {
    domain_name              = data.aws_s3_bucket.media.bucket_regional_domain_name
    origin_id                = "media-s3-origin"
    origin_access_control_id = aws_cloudfront_origin_access_control.media[0].id
  }

  default_cache_behavior {
    target_origin_id       = "media-s3-origin"
    viewer_protocol_policy = "redirect-to-https"
    compress               = true

    allowed_methods = ["GET", "HEAD", "OPTIONS"]
    cached_methods  = ["GET", "HEAD", "OPTIONS"]

    forwarded_values {
      query_string = false

      cookies {
        forward = "none"
      }
    }
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  viewer_certificate {
    cloudfront_default_certificate = true
  }
}

data "aws_iam_policy_document" "cloudfront_bucket_policy" {
  count = var.enable_cloudfront && var.manage_cloudfront_bucket_policy ? 1 : 0

  statement {
    sid    = "AllowCloudFrontReadMedia"
    effect = "Allow"
    actions = [
      "s3:GetObject",
    ]
    resources = [
      "arn:aws:s3:::${var.bucket_name}/media/*",
    ]

    principals {
      type        = "Service"
      identifiers = ["cloudfront.amazonaws.com"]
    }

    condition {
      test     = "StringEquals"
      variable = "AWS:SourceArn"
      values   = [aws_cloudfront_distribution.media[0].arn]
    }
  }
}

resource "aws_s3_bucket_policy" "cloudfront_read_media" {
  count  = var.enable_cloudfront && var.manage_cloudfront_bucket_policy ? 1 : 0
  bucket = data.aws_s3_bucket.media.id
  policy = data.aws_iam_policy_document.cloudfront_bucket_policy[0].json
}
