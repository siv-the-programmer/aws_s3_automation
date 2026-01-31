# S3 Bucket Creator

This project contains a single Python script that creates an Amazon S3 bucket using boto3.

The purpose is to learn and understand S3 bucket creation before moving on to uploads, hosting, or CloudFront.

Nothing else happens in this script.

No files are uploaded.  
No hosting is enabled.  
The bucket remains private.

---

## File

s3_create.py

---

## What the Script Does

- Prompts for an S3 bucket name  
- Validates basic bucket naming rules  
- Checks if the bucket name already exists globally  
- Creates the bucket in the selected AWS region  
- Confirms successful creation  

---

## Requirements

- Python 3.10 or newer  
- AWS CLI configured with valid credentials  
- boto3 installed  

---

## Setup

Create a virtual environment and install dependencies:

```
python3 -m venv .venv
. .venv/bin/activate
pip install boto3

```

# Configure AWS credentials:

aws configure
Usage
Run the script:
```
python3 s3_create.py
Enter a bucket name when prompted.
```
# Bucket names must:

Be globally unique across all AWS accounts

Contain only lowercase letters, numbers, and hyphens

Not contain spaces or underscores

Be between 3 and 63 characters

Example:
```
my-s3-bucket-2026
If the name is already taken, AWS will reject it and you must choose another.
```
# Result:
After successful execution:

The S3 bucket exists in your AWS account

The bucket is private by default

No files are uploaded

No public access is enabled

You can verify creation in:

AWS Console → S3 → Buckets

# Important Notes

S3 bucket names are global, not per region

Bucket creation is free

You pay only for storage and requests after uploading files

A bucket must be empty before it can be deleted

# Security
Do not commit the following to GitHub:

~/.aws/credentials

.env files

private keys (*.pem, *.key)

Use a .gitignore file to prevent accidental leaks.

# Learning Path
# Recommended order:

Create bucket

Understand regions and naming

Upload files manually

Automate uploads with Python

Enable static hosting

Add CloudFront HTTPS

One concept at a time.