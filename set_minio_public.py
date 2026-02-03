#!/usr/bin/env python
"""
Set MinIO bucket to anonymous read policy (download only)
This allows images to be accessed via direct URLs without presigned signatures
"""
import json
from minio import Minio

# MinIO connection (internal)
client = Minio(
    "minio:9000",
    access_key="foodlife_admin",
    secret_key="foodlife_secret_2026",
    secure=False
)

bucket_name = "product-images"

# Anonymous read-only policy (download access only)
policy = {
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {"AWS": "*"},
            "Action": ["s3:GetObject"],
            "Resource": [f"arn:aws:s3:::{bucket_name}/*"]
        }
    ]
}

policy_json = json.dumps(policy)

print(f"Setting bucket '{bucket_name}' to anonymous read policy...")
print(f"Policy: {policy_json}")

try:
    client.set_bucket_policy(bucket_name, policy_json)
    print(f"✓ Bucket '{bucket_name}' is now publicly readable")
    print(f"  Images can be accessed via: http://localhost:9000/{bucket_name}/object-key")
except Exception as e:
    print(f"✗ Error: {e}")
