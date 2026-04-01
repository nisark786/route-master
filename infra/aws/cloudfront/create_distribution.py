import json
import os
import sys
import time
import uuid

import boto3
from botocore.exceptions import ClientError


def required_env(name):
    value = os.getenv(name, "").strip()
    if not value:
        raise SystemExit(f"Missing required environment variable: {name}")
    return value


def main():
    bucket = required_env("AWS_STORAGE_BUCKET_NAME")
    region = required_env("AWS_S3_REGION_NAME")
    price_class = os.getenv("CLOUDFRONT_PRICE_CLASS", "PriceClass_200")
    comment = os.getenv("CLOUDFRONT_COMMENT", f"RouteMaster media CDN for {bucket}")

    cloudfront = boto3.client("cloudfront")
    s3 = boto3.client("s3", region_name=region)
    sts = boto3.client("sts")
    account_id = sts.get_caller_identity()["Account"]

    bucket_domain_name = f"{bucket}.s3.{region}.amazonaws.com"
    caller_reference = f"route-management-{bucket}-{int(time.time())}"

    oac_name = f"{bucket}-media-oac"
    print(f"Creating Origin Access Control: {oac_name}")
    oac = cloudfront.create_origin_access_control(
        OriginAccessControlConfig={
            "Name": oac_name,
            "Description": f"OAC for {bucket} media delivery",
            "SigningProtocol": "sigv4",
            "SigningBehavior": "always",
            "OriginAccessControlOriginType": "s3",
        }
    )["OriginAccessControl"]

    oac_id = oac["Id"]
    print(f"OAC created: {oac_id}")

    print("Creating CloudFront distribution...")
    distribution = cloudfront.create_distribution(
        DistributionConfig={
            "CallerReference": caller_reference,
            "Comment": comment,
            "Enabled": True,
            "PriceClass": price_class,
            "Origins": {
                "Quantity": 1,
                "Items": [
                    {
                        "Id": "media-s3-origin",
                        "DomainName": bucket_domain_name,
                        "S3OriginConfig": {"OriginAccessIdentity": ""},
                        "OriginAccessControlId": oac_id,
                    }
                ],
            },
            "DefaultCacheBehavior": {
                "TargetOriginId": "media-s3-origin",
                "ViewerProtocolPolicy": "redirect-to-https",
                "AllowedMethods": {
                    "Quantity": 3,
                    "Items": ["GET", "HEAD", "OPTIONS"],
                    "CachedMethods": {
                        "Quantity": 3,
                        "Items": ["GET", "HEAD", "OPTIONS"],
                    },
                },
                "Compress": True,
                "ForwardedValues": {
                    "QueryString": False,
                    "Cookies": {"Forward": "none"},
                },
                "TrustedSigners": {"Enabled": False, "Quantity": 0},
                "MinTTL": 0,
            },
            "ViewerCertificate": {"CloudFrontDefaultCertificate": True},
        }
    )["Distribution"]

    distribution_id = distribution["Id"]
    distribution_domain = distribution["DomainName"]
    distribution_arn = f"arn:aws:cloudfront::{account_id}:distribution/{distribution_id}"
    print(f"Distribution created: {distribution_id}")
    print(f"Domain: {distribution_domain}")

    bucket_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "AllowCloudFrontReadMedia",
                "Effect": "Allow",
                "Principal": {"Service": "cloudfront.amazonaws.com"},
                "Action": "s3:GetObject",
                "Resource": f"arn:aws:s3:::{bucket}/media/*",
                "Condition": {
                    "StringEquals": {
                        "AWS:SourceArn": distribution_arn,
                    }
                },
            }
        ],
    }

    print("Applying bucket policy for CloudFront OAC...")
    s3.put_bucket_policy(Bucket=bucket, Policy=json.dumps(bucket_policy))

    print("")
    print("Done.")
    print(f"AWS_S3_CUSTOM_DOMAIN={distribution_domain}")
    print("Set AWS_QUERYSTRING_AUTH=False after switching reads to CloudFront.")
    print("CloudFront deployment may take several minutes to finish.")


if __name__ == "__main__":
    try:
        main()
    except ClientError as exc:
        print(f"AWS error: {exc}", file=sys.stderr)
        raise
