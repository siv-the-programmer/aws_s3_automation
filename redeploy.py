#!/usr/bin/env python3
import os
import sys
import time
import mimetypes

import boto3
from botocore.exceptions import ClientError

REGION = "eu-north-1"
CF_REGION = "us-east-1"
SITE_DIR = "sites"


def die(msg: str, code: int = 1):
    print(f"\nERROR: {msg}\n", file=sys.stderr)
    sys.exit(code)


def ensure_site_folder():
    if not os.path.isdir(SITE_DIR):
        die(f"Missing folder: ./{SITE_DIR}")

    index_path = os.path.join(SITE_DIR, "index.html")
    if not os.path.isfile(index_path):
        die(f"Missing file: ./{SITE_DIR}/index.html")


def make_clients():
    session = boto3.session.Session(region_name=REGION)
    s3 = session.client("s3", endpoint_url=f"https://s3.{REGION}.amazonaws.com")
    cf = session.client("cloudfront", region_name=CF_REGION)
    return s3, cf


def check_bucket_access(s3, bucket: str):
    try:
        s3.head_bucket(Bucket=bucket)
    except ClientError as e:
        status = e.response.get("ResponseMetadata", {}).get("HTTPStatusCode")
        if status == 403:
            die("Bucket exists but you don't have access (403). Check your AWS credentials/permissions.")
        if status == 404:
            die("Bucket not found (404). Check the bucket name.")
        die("Could not access the bucket. Check name and permissions.")


def upload_sites_folder(s3, bucket: str) -> int:
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

            try:
                if extra:
                    s3.upload_file(local_path, bucket, key, ExtraArgs=extra)
                else:
                    s3.upload_file(local_path, bucket, key)
            except ClientError as e:
                code = e.response.get("Error", {}).get("Code", "ClientError")
                die(f"Upload failed for '{key}' (AWS: {code}).")

            print(f"Uploaded: {key}")
            uploaded += 1

    return uploaded


def invalidate_cloudfront(cf, dist_id: str):
    try:
        cf.create_invalidation(
            DistributionId=dist_id,
            InvalidationBatch={
                "CallerReference": f"redeploy-{int(time.time())}",
                "Paths": {"Quantity": 1, "Items": ["/*"]},
            },
        )
    except ClientError as e:
        code = e.response.get("Error", {}).get("Code", "ClientError")
        die(f"CloudFront invalidation failed (AWS: {code}). Check Distribution ID and permissions.")

    print("CloudFront invalidation sent: /*")


def main():
    print("\nRedeploy (upload ./sites to S3, optional CloudFront refresh)\n")

    ensure_site_folder()

    bucket = input("Bucket name: ").strip()
    if not bucket:
        die("Bucket name is required.")

    dist_id = input("CloudFront Distribution ID (press Enter to skip): ").strip()

    s3, cf = make_clients()

    print("Checking bucket access...")
    check_bucket_access(s3, bucket)
    print("Bucket access OK")

    print("Uploading files...")
    count = upload_sites_folder(s3, bucket)
    print(f"Uploaded {count} file(s)")

    if dist_id:
        print("Refreshing CloudFront...")
        invalidate_cloudfront(cf, dist_id)
    else:
        print("Skipped CloudFront refresh")

    print("\nDONE\n")


if __name__ == "__main__":
    main()
