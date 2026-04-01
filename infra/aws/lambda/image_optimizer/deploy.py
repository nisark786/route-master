import json
import os
import sys
import time
from pathlib import Path

import boto3
from botocore.exceptions import ClientError


DEFAULT_FUNCTION_NAME = "route-management-image-optimizer"
DEFAULT_ROLE_NAME = "route-management-image-optimizer-role"
DEFAULT_RUNTIME = "python3.12"
DEFAULT_HANDLER = "handler.lambda_handler"
DEFAULT_TIMEOUT = 30
DEFAULT_MEMORY = 512
DEFAULT_MAX_DIMENSION = "1600"
DEFAULT_JPEG_QUALITY = "82"
DEFAULT_WEBP_QUALITY = "80"
DEFAULT_PNG_MAX_COLORS = "256"


def required_env(name):
    value = os.getenv(name, "").strip()
    if not value:
        raise SystemExit(f"Missing required environment variable: {name}")
    return value


def load_package_bytes():
    package_path = os.getenv("LAMBDA_PACKAGE_PATH", "").strip()
    if not package_path:
        package_path = str(Path(__file__).resolve().parent / "build" / "image-optimizer.zip")

    package_file = Path(package_path)
    if not package_file.exists():
        raise SystemExit(
            f"Lambda package not found at {package_file}. "
            "Build it first with package.ps1 or set LAMBDA_PACKAGE_PATH."
        )

    return package_file.read_bytes()


def ensure_role(iam, account_id, bucket):
    role_name = os.getenv("LAMBDA_ROLE_NAME", DEFAULT_ROLE_NAME)
    assume_role_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {"Service": "lambda.amazonaws.com"},
                "Action": "sts:AssumeRole",
            }
        ],
    }

    role_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "AllowCloudWatchLogs",
                "Effect": "Allow",
                "Action": [
                    "logs:CreateLogGroup",
                    "logs:CreateLogStream",
                    "logs:PutLogEvents",
                ],
                "Resource": [
                    f"arn:aws:logs:*:{account_id}:*",
                ],
            },
            {
                "Sid": "AllowMediaObjectReadWrite",
                "Effect": "Allow",
                "Action": [
                    "s3:GetObject",
                    "s3:PutObject",
                    "s3:HeadObject",
                ],
                "Resource": [
                    f"arn:aws:s3:::{bucket}/media/products/*",
                    f"arn:aws:s3:::{bucket}/media/shops/*",
                ],
            },
        ],
    }

    try:
        role = iam.get_role(RoleName=role_name)["Role"]
        iam.update_assume_role_policy(
            RoleName=role_name,
            PolicyDocument=json.dumps(assume_role_policy),
        )
    except iam.exceptions.NoSuchEntityException:
        role = iam.create_role(
            RoleName=role_name,
            AssumeRolePolicyDocument=json.dumps(assume_role_policy),
            Description="Execution role for Route Management S3 image optimizer Lambda",
        )["Role"]
        # IAM propagation delay is common after fresh role creation.
        time.sleep(10)

    iam.put_role_policy(
        RoleName=role_name,
        PolicyName="route-management-image-optimizer-inline",
        PolicyDocument=json.dumps(role_policy),
    )
    return role["Arn"]


def ensure_function(lambda_client, role_arn, package_bytes, bucket, region):
    function_name = os.getenv("LAMBDA_FUNCTION_NAME", DEFAULT_FUNCTION_NAME)
    timeout = int(os.getenv("LAMBDA_TIMEOUT", str(DEFAULT_TIMEOUT)))
    memory = int(os.getenv("LAMBDA_MEMORY_MB", str(DEFAULT_MEMORY)))
    env_vars = {
        "MAX_DIMENSION": os.getenv("MAX_DIMENSION", DEFAULT_MAX_DIMENSION),
        "JPEG_QUALITY": os.getenv("JPEG_QUALITY", DEFAULT_JPEG_QUALITY),
        "WEBP_QUALITY": os.getenv("WEBP_QUALITY", DEFAULT_WEBP_QUALITY),
        "PNG_MAX_COLORS": os.getenv("PNG_MAX_COLORS", DEFAULT_PNG_MAX_COLORS),
    }

    function_kwargs = {
        "FunctionName": function_name,
        "Role": role_arn,
        "Runtime": DEFAULT_RUNTIME,
        "Handler": DEFAULT_HANDLER,
        "Code": {"ZipFile": package_bytes},
        "Description": "Optimizes product/shop images uploaded to S3",
        "Timeout": timeout,
        "MemorySize": memory,
        "Publish": True,
        "Environment": {"Variables": env_vars},
        "Architectures": ["x86_64"],
    }

    try:
        function = lambda_client.get_function(FunctionName=function_name)["Configuration"]
        lambda_client.update_function_code(
            FunctionName=function_name,
            ZipFile=package_bytes,
            Publish=True,
        )
        waiter = lambda_client.get_waiter("function_updated")
        waiter.wait(FunctionName=function_name)
        lambda_client.update_function_configuration(
            FunctionName=function_name,
            Role=role_arn,
            Runtime=DEFAULT_RUNTIME,
            Handler=DEFAULT_HANDLER,
            Description="Optimizes product/shop images uploaded to S3",
            Timeout=timeout,
            MemorySize=memory,
            Environment={"Variables": env_vars},
        )
        waiter.wait(FunctionName=function_name)
        function = lambda_client.get_function(FunctionName=function_name)["Configuration"]
    except lambda_client.exceptions.ResourceNotFoundException:
        function = lambda_client.create_function(**function_kwargs)
        waiter = lambda_client.get_waiter("function_active_v2")
        waiter.wait(FunctionName=function_name)
        function = lambda_client.get_function(FunctionName=function_name)["Configuration"]

    add_invoke_permission(lambda_client, function_name, bucket, region)
    return function["FunctionArn"]


def add_invoke_permission(lambda_client, function_name, bucket, region):
    statement_id = "AllowExecutionFromS3Bucket"
    source_arn = f"arn:aws:s3:::{bucket}"
    source_account = boto3.client("sts").get_caller_identity()["Account"]

    try:
        lambda_client.add_permission(
            FunctionName=function_name,
            StatementId=statement_id,
            Action="lambda:InvokeFunction",
            Principal="s3.amazonaws.com",
            SourceArn=source_arn,
            SourceAccount=source_account,
        )
    except ClientError as exc:
        error_code = exc.response.get("Error", {}).get("Code")
        if error_code != "ResourceConflictException":
            raise


def ensure_bucket_notifications(s3, function_arn, bucket):
    response = s3.get_bucket_notification_configuration(Bucket=bucket)

    lambda_configs = [
        config
        for config in response.get("LambdaFunctionConfigurations", [])
        if config.get("Id") not in {"route-management-products-image-optimizer", "route-management-shops-image-optimizer"}
    ]

    lambda_configs.extend(
        [
            {
                "Id": "route-management-products-image-optimizer",
                "LambdaFunctionArn": function_arn,
                "Events": ["s3:ObjectCreated:*"],
                "Filter": {
                    "Key": {
                        "FilterRules": [
                            {"Name": "prefix", "Value": "media/products/"},
                        ]
                    }
                },
            },
            {
                "Id": "route-management-shops-image-optimizer",
                "LambdaFunctionArn": function_arn,
                "Events": ["s3:ObjectCreated:*"],
                "Filter": {
                    "Key": {
                        "FilterRules": [
                            {"Name": "prefix", "Value": "media/shops/"},
                        ]
                    }
                },
            },
        ]
    )

    notification_configuration = {}
    if response.get("TopicConfigurations"):
        notification_configuration["TopicConfigurations"] = response["TopicConfigurations"]
    if response.get("QueueConfigurations"):
        notification_configuration["QueueConfigurations"] = response["QueueConfigurations"]
    notification_configuration["LambdaFunctionConfigurations"] = lambda_configs

    s3.put_bucket_notification_configuration(
        Bucket=bucket,
        NotificationConfiguration=notification_configuration,
    )


def main():
    bucket = required_env("AWS_STORAGE_BUCKET_NAME")
    region = required_env("AWS_S3_REGION_NAME")
    package_bytes = load_package_bytes()

    session = boto3.Session(region_name=region)
    sts = session.client("sts")
    iam = session.client("iam")
    lambda_client = session.client("lambda")
    s3 = session.client("s3")

    account_id = sts.get_caller_identity()["Account"]
    role_arn = ensure_role(iam, account_id, bucket)
    function_arn = ensure_function(lambda_client, role_arn, package_bytes, bucket, region)
    ensure_bucket_notifications(s3, function_arn, bucket)

    print("")
    print("Done.")
    print(f"LAMBDA_FUNCTION_NAME={os.getenv('LAMBDA_FUNCTION_NAME', DEFAULT_FUNCTION_NAME)}")
    print(f"LAMBDA_FUNCTION_ARN={function_arn}")
    print(f"S3_BUCKET={bucket}")
    print("Attached triggers:")
    print("- media/products/")
    print("- media/shops/")


if __name__ == "__main__":
    try:
        main()
    except ClientError as exc:
        print(f"AWS error: {exc}", file=sys.stderr)
        raise
