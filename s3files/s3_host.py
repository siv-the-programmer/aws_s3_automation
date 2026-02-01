#!/usr/bin/env python3
import os
import sys
import json
import time
import mimetypes

import boto3
from botocore.exceptions import ClientError

REGION = "eu-north-1"
SITE_DIR = "sites"
CF_REGION = "us-east-1"

CACHE_POLICY_CACHING_OPTIMIZED = "658327ea-f89d-4fab-a63d-7e88639e58f6"
ORIGIN_REQUEST_POLICY_CORS_S3 = "88a5eaf4-2fd4-4709-b370-b4c650ea3fcf"


def say(msg: str):
    print(msg)


def stop(msg: str, code: int = 1):
    print(msg)
    sys.exit(code)


def safe_aws_call(fn, friendly_fail_msg: str):
    try:
        return fn()
    except ClientError:
        stop(friendly_fail_msg)
    except Exception:
        stop(friendly_fail_msg)


def check_site_folder():
    if not os.path.isdir(SITE_DIR):
        stop(f"Missing folder: ./{SITE_DIR}")
    if not os.path.isfile(os.path.join(SITE_DIR, "index.html")):
        stop(f"Missing file: ./{SITE_DIR}/index.html")


def get_clients():
    session = boto3.session.Session(region_name=REGION)
    s3 = session.client("s3", endpoint_url=f"https://s3.{REGION}.amazonaws.com")
    cf = session.client("cloudfront", region_name=CF_REGION)
    return s3, cf


def bucket_access_ok(s3, bucket: str) -> bool:
    try:
        s3.head_bucket(Bucket=bucket)
        return True
    except ClientError:
        return False


def upload_folder_to_s3(s3, bucket: str) -> int:
    uploaded = 0

    for root, _, files in os.walk(SITE_DIR):
        for filename in files:
            local_path = os.path.join(root, filename)
            key = os.path.relpath(local_path, SITE_DIR).replace(os.sep, "/")

            content_type, _ = mimetypes.guess_type(local_path)

            extra = {}
            if content_type:
                extra["ContentType"] = content_type

            if key.endswith(".html"):
                extra["CacheControl"] = "no-cache"
            else:
                extra["CacheControl"] = "public, max-age=86400"

            def do_upload():
                if extra:
                    return s3.upload_file(local_path, bucket, key, ExtraArgs=extra)
                return s3.upload_file(local_path, bucket, key)

            safe_aws_call(do_upload, "Upload failed.")

            uploaded += 1
            say(f"Uploaded: {key}")

    return uploaded


def lock_bucket_private(s3, bucket: str):
    def do_pab():
        return s3.put_public_access_block(
            Bucket=bucket,
            PublicAccessBlockConfiguration={
                "BlockPublicAcls": True,
                "IgnorePublicAcls": True,
                "BlockPublicPolicy": True,
                "RestrictPublicBuckets": True,
            },
        )

    safe_aws_call(do_pab, "Could not lock bucket.")

    try:
        s3.delete_bucket_website(Bucket=bucket)
    except ClientError:
        pass

    try:
        s3.delete_bucket_policy(Bucket=bucket)
    except ClientError:
        pass


def create_oac(cf) -> str:
    def do_oac():
        return cf.create_origin_access_control(
            OriginAccessControlConfig={
                "Name": f"oac-s3-{int(time.time())}",
                "Description": "OAC for private S3 origin",
                "SigningProtocol": "sigv4",
                "SigningBehavior": "always",
                "OriginAccessControlOriginType": "s3",
            }
        )

    resp = safe_aws_call(do_oac, "Could not create OAC.")
    return resp["OriginAccessControl"]["Id"]


def create_distribution(cf, bucket: str, oac_id: str):
    origin_domain = f"{bucket}.s3.{REGION}.amazonaws.com"
    origin_id = f"S3-{bucket}"
    caller_ref = f"deploy-{bucket}-{int(time.time())}"

    config = {
        "CallerReference": caller_ref,
        "Comment": f"Secure static site for {bucket}",
        "Enabled": True,
        "DefaultRootObject": "index.html",
        "HttpVersion": "http2and3",
        "PriceClass": "PriceClass_100",
        "IsIPV6Enabled": True,
        "ViewerCertificate": {"CloudFrontDefaultCertificate": True},
        "Origins": {
            "Quantity": 1,
            "Items": [
                {
                    "Id": origin_id,
                    "DomainName": origin_domain,
                    "OriginAccessControlId": oac_id,
                    "S3OriginConfig": {"OriginAccessIdentity": ""},
                }
            ],
        },
        "DefaultCacheBehavior": {
            "TargetOriginId": origin_id,
            "ViewerProtocolPolicy": "redirect-to-https",
            "Compress": True,
            "AllowedMethods": {
                "Quantity": 2,
                "Items": ["GET", "HEAD"],
                "CachedMethods": {"Quantity": 2, "Items": ["GET", "HEAD"]},
            },
            "CachePolicyId": CACHE_POLICY_CACHING_OPTIMIZED,
            "OriginRequestPolicyId": ORIGIN_REQUEST_POLICY_CORS_S3,
        },
    }

    def do_dist():
        return cf.create_distribution(DistributionConfig=config)

    resp = safe_aws_call(do_dist, "Could not create CloudFront distribution.")
    dist = resp["Distribution"]
    return dist["Id"], dist["DomainName"], dist["ARN"]


def set_bucket_policy_for_cf(s3, bucket: str, dist_arn: str):
    policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "AllowCloudFrontReadOnly",
                "Effect": "Allow",
                "Principal": {"Service": "cloudfront.amazonaws.com"},
                "Action": "s3:GetObject",
                "Resource": f"arn:aws:s3:::{bucket}/*",
                "Condition": {"StringEquals": {"AWS:SourceArn": dist_arn}},
            }
        ],
    }

    def do_policy():
        return s3.put_bucket_policy(Bucket=bucket, Policy=json.dumps(policy))

    safe_aws_call(do_policy, "Could not set bucket policy.")


def invalidate_all(cf, dist_id: str):
    def do_inval():
        return cf.create_invalidation(
            DistributionId=dist_id,
            InvalidationBatch={
                "CallerReference": f"inval-{int(time.time())}",
                "Paths": {"Quantity": 1, "Items": ["/*"]},
            },
        )

    safe_aws_call(do_inval, "Could not invalidate cache.")


def main():
    check_site_folder()

    bucket = input("Bucket name: ").strip()
    if not bucket:
        stop("Bucket name required.")

    s3, cf = get_clients()

    if not bucket_access_ok(s3, bucket):
        stop("Bucket not accessible.")

    count = upload_folder_to_s3(s3, bucket)
    print(f"Uploaded {count} file(s).")

    lock_bucket_private(s3, bucket)

    oac_id = create_oac(cf)

    dist_id, domain, dist_arn = create_distribution(cf, bucket, oac_id)

    set_bucket_policy_for_cf(s3, bucket, dist_arn)

    invalidate_all(cf, dist_id)

    print("DONE")
    print(f"https://{domain}/")


if __name__ == "__main__":
    main()
