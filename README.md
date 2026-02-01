# Secure S3 + CloudFront Static Site Deployer (Python + boto3)
![Python](https://img.shields.io/badge/Python-3.x-blue?logo=python&logoColor=white)
![AWS IAM](https://img.shields.io/badge/AWS-IAM-orange?logo=amazonaws&logoColor=white)
![AWS](https://img.shields.io/badge/AWS-Cloud-orange?logo=amazonaws&logoColor=white)
![Boto3](https://img.shields.io/badge/Boto3-AWS%20SDK-yellow)
![Automation](https://img.shields.io/badge/Focus-Automation-green)


This repo is a **free-tier-friendly** static website deployer that:

- **Creates an S3 bucket** (from `s3_create.py`)
- **Uploads your site files** from `./sites/` to S3
- **Locks the bucket private** (no public website hosting)
- **Creates a CloudFront distribution** in front of the private S3 bucket (OAC)
- **Applies the correct S3 bucket policy** so CloudFront can read your files
- **Invalidates CloudFront cache** so updates show immediately

Result: a **secure HTTPS site** on a CloudFront domain, with your S3 bucket kept private.

---

## Why this setup (mental model)

- **S3** stores your files (origin).
- **CloudFront** is the public “front door” (CDN) that serves the site over HTTPS.
- **OAC (Origin Access Control)** is the “VIP pass” that lets CloudFront fetch from your **private** S3 bucket.
- **Bucket policy** is the “bouncer rule” that only allows CloudFront to read your objects.

No public S3 website endpoint. No public bucket. That’s the right way.

---

## Project structure

.
├── sites/
│ ├── index.html
│ ├── style.css
│ └── (any other assets: js, images, etc)
├── s3_create.py
├── s3_host.py
└── README.md


**Important:** `./sites/index.html` must exist or the deployer stops.

---

## Requirements

- Python 3.10+ recommended
- AWS CLI configured (or environment creds set)
- boto3 installed
- AWS account with permissions for:
  - S3 (create bucket, upload objects, policies, public access block)
  - CloudFront (OAC, distribution, invalidations)

---

## Install

### 1) Create a virtual environment (recommended)

```bash
python3 -m venv .venv
. .venv/bin/activate
2) Install dependencies
python3 -m pip install --upgrade pip
python3 -m pip install boto3
3) Configure AWS credentials
Use one of these approaches:

Option A: AWS CLI profile

aws configure
Option B: Environment variables

export AWS_ACCESS_KEY_ID="..."
export AWS_SECRET_ACCESS_KEY="..."
export AWS_DEFAULT_REGION="eu-north-1"
Step 1 — Create the bucket (s3_create.py)
This script should:

Validate bucket naming rules

Create the S3 bucket in eu-north-1

Optionally enable basic safe defaults (recommended)

Run:
```python3 s3_create.py
```


When it asks for a bucket name, use something globally unique, lowercase, no underscores:

Good: siv-static-site-2026-01

Bad: Siv_Site, my bucket, test_bucket

After creation, keep the bucket name — you’ll need it in the next step.

# Step 2 — Deploy + Secure + CloudFront (s3_host.py)
This script does the real work:

What it does (in order)
Validates site folder

Requires ./sites/ and ./sites/index.html

Uploads everything under ./sites/

Preserves folder structure

Sets ContentType using mimetypes

# Sets cache headers:

*.html → CacheControl: no-cache (so page updates appear fast)

assets (css/js/img) → CacheControl: public, max-age=86400

Locks the bucket private

Applies S3 Public Access Block

Removes any website config + bucket policy leftovers

Creates CloudFront OAC

CloudFront signs requests to S3 using SigV4

Creates a CloudFront distribution

HTTPS enforced (redirect-to-https)

HTTP/2 + HTTP/3 enabled

PriceClass_100 (cheaper regions)

Default root object = index.html

Sets S3 bucket policy

Allows ONLY CloudFront service principal to s3:GetObject

Condition restricts access to the specific distribution ARN

Invalidates cache

Creates invalidation for /*

Run:
```
python3 s3_host.py
```
# Enter the bucket name you created.

Output includes the CloudFront URL:

https://dxxxxxxxxxxxxx.cloudfront.net/
Updating the site (redeploy)
Edit files inside ./sites/

# Run again:

python3 s3_host.py
This re-uploads your files and invalidates cache.

# Note: the current script creates a new CloudFront distribution each run (because it always creates a new OAC + distribution). That works, but it’s not ideal long-term.

Cost + Free-tier reality check (read this)
S3: cheap and has free-tier, but not “free forever” in every scenario.

CloudFront: has a free tier, but it is not unlimited and not forever at high traffic.

This setup is “free-tier-friendly,” not “guaranteed zero cost.”

# Best practice:

Use AWS Budgets + alerts (recommended)

Delete old CloudFront distributions you don’t need

# Common problems
1) “Missing folder: ./sites”
Create it and add index.html:

mkdir -p sites
printf '<!doctype html><html><body><h1>It works</h1></body></html>\n' > sites/index.html
2) “Bucket not accessible”
Bucket doesn’t exist

You typed it wrong

You don’t own it (name taken)

Your AWS credentials lack permissions

3) Changes not showing
CloudFront caches aggressively. This script runs an invalidation (/*), but also:

Hard refresh browser

Wait a minute

Confirm you uploaded the right file into sites/

Security notes (why this is correct)
Bucket is private (Public Access Block on)

Access is only via CloudFront OAC + strict bucket policy

HTTPS enforced at the edge

No public S3 website endpoint

This is the “don’t get embarrassed in a security review” version of static hosting.

# Next upgrades (recommended)
Stop creating a new distribution every deploy

Store dist_id, dist_arn, domain, oac_id in a local state file (e.g., .deploy-state.json)

Reuse the same distribution and just invalidate + upload

Add AWS Budgets automation

Create a budget + alert at $3

Notify via email or SNS

Add CI/CD

GitHub Actions → deploy on push to main

Custom domain

Use ACM cert in us-east-1 + CloudFront alternate domain names

DNS via Route 53 or Cloudflare (depending on your constraints)

# Files explained
```
s3_create.py
Creates the S3 bucket (and should enforce naming/region rules).

s3_host.py
Uploads ./sites/ to S3, locks bucket private, sets up CloudFront OAC + distribution, and invalidates cache.
```

# Quick start
python3 s3_create.py
python3 s3_host.py

Put your site in ./sites/ and make sure ./sites/index.html exists.
