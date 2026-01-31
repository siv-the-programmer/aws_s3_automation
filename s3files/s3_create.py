import sys
import boto3
from botocore.exceptions import ClientError

REGION = "eu-north-1"

def die(msg):
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(1)
    
def main():
    bucket = input("Enter new bucket name: ").strip()

    if "_" in bucket or bucket.lower() != bucket:
        die("Bucket name must be lowercase and contain no underscores.")

    session = boto3.session.Session(region_name=REGION)
    s3 = session.client("s3", endpoint_url=f"https://s3.{REGION}.amazonaws.com")

    try:
        s3.head_bucket(Bucket=bucket)
        die("Bucket already exists.")
    except ClientError as e:
        status = e.response.get("ResponseMetadata", {}).get("HTTPStatusCode")
        if status == 403:
            die("Bucket name already taken. Choose another.")
        if status != 404:
            die("Unexpected error checking bucket.")

    print(f"Creating bucket in {REGION}...")

    try:
        s3.create_bucket(
            Bucket=bucket,
            CreateBucketConfiguration={
                "LocationConstraint": REGION
            }
        )
    except ClientError as e:
        die(f"Create bucket failed: {e}")

    print("Bucket created successfully.")

    print(f"Bucket name is : {bucket}")
    
if __name__ == "__main__":
    main()
