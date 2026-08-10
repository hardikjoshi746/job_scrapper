import boto3
from botocore.exceptions import ClientError
from config import settings

def _client():
    return boto3.client(
        "s3",
        region_name=settings.aws_region,
        aws_access_key_id=settings.aws_access_key_id,
        aws_secret_access_key=settings.aws_secret_access_key,
    )


def upload_file(local_path: str, s3_key: str) -> str:
    """Upload a local file to S3 and return the S3 key."""
    _client().upload_file(local_path, settings.s3_bucket, s3_key)
    return s3_key


def upload_bytes(data: bytes, s3_key: str, content_type: str = "application/octet-stream") -> str:
    """Upload bytes directly to S3 and return the S3 key."""
    _client().put_object(
        Bucket=settings.s3_bucket,
        Key=s3_key,
        Body=data,
        ContentType=content_type,
    )
    return s3_key


def get_presigned_url(s3_key: str, expires_in: int = 3600) -> str:
    """Generate a presigned download URL (default 1 hour)."""
    return _client().generate_presigned_url(
        "get_object",
        Params={"Bucket": settings.s3_bucket, "Key": s3_key},
        ExpiresIn=expires_in,
    )
