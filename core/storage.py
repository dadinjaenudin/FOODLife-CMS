"""
MinIO Storage Service - Handle object storage for images
Vibe coding - plain mode: simple, direct, no over-engineering
"""
import os
import hashlib
import uuid
from minio import Minio
from minio.error import S3Error
from django.conf import settings
from io import BytesIO


class MinIOStorage:
    """
    Simple MinIO wrapper for image upload/download
    - Upload image to MinIO
    - Get image URL
    - Delete image
    - List images
    """
    
    def __init__(self):
        """Initialize MinIO client"""
        self.client = Minio(
            settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=settings.MINIO_USE_SSL
        )
        self.bucket_products = settings.MINIO_BUCKET_PRODUCTS
        
        # Ensure bucket exists
        self._ensure_bucket_exists(self.bucket_products)
    
    def _ensure_bucket_exists(self, bucket_name):
        """Create bucket if not exists"""
        try:
            if not self.client.bucket_exists(bucket_name):
                self.client.make_bucket(bucket_name)
                print(f"✓ MinIO bucket '{bucket_name}' created")
        except S3Error as e:
            print(f"✗ MinIO bucket error: {e}")
    
    def upload_product_image(self, file, product_id, is_primary=False):
        """
        Upload product image to MinIO
        
        Args:
            file: Django UploadedFile object
            product_id: Product UUID
            is_primary: Whether this is primary image
            
        Returns:
            dict: {
                'object_key': 'products/uuid/filename.jpg',
                'size': 12345,
                'content_type': 'image/jpeg',
                'checksum': 'md5hash',
                'version': 1
            }
        """
        try:
            # Generate object key: products/{product_id}/{uuid}_{filename}
            file_uuid = uuid.uuid4().hex[:8]
            ext = os.path.splitext(file.name)[1].lower()
            filename = f"{file_uuid}_{file.name}" if not is_primary else f"primary{ext}"
            object_key = f"products/{product_id}/{filename}"
            
            # Calculate MD5 checksum
            file.seek(0)
            file_data = file.read()
            checksum = hashlib.md5(file_data).hexdigest()
            
            # Upload to MinIO
            file.seek(0)
            self.client.put_object(
                bucket_name=self.bucket_products,
                object_name=object_key,
                data=BytesIO(file_data),
                length=len(file_data),
                content_type=file.content_type or 'image/jpeg'
            )
            
            return {
                'object_key': object_key,
                'size': len(file_data),
                'content_type': file.content_type or 'image/jpeg',
                'checksum': checksum,
                'version': 1,
                'filename': file.name
            }
            
        except S3Error as e:
            print(f"✗ MinIO upload error: {e}")
            raise Exception(f"Failed to upload image: {e}")
    
    def get_image_url(self, object_key, expires=3600):
        """
        Get presigned URL for image access
        
        Args:
            object_key: Object key in MinIO
            expires: URL expiration in seconds (default 1 hour)
            
        Returns:
            str: Presigned URL
        """
        try:
            url = self.client.presigned_get_object(
                bucket_name=self.bucket_products,
                object_name=object_key,
                expires=expires
            )
            return url
        except S3Error as e:
            print(f"✗ MinIO get URL error: {e}")
            return None
    
    def delete_image(self, object_key):
        """Delete image from MinIO"""
        try:
            self.client.remove_object(
                bucket_name=self.bucket_products,
                object_name=object_key
            )
            return True
        except S3Error as e:
            print(f"✗ MinIO delete error: {e}")
            return False
    
    def list_product_images(self, product_id):
        """List all images for a product"""
        try:
            prefix = f"products/{product_id}/"
            objects = self.client.list_objects(
                bucket_name=self.bucket_products,
                prefix=prefix
            )
            return [obj.object_name for obj in objects]
        except S3Error as e:
            print(f"✗ MinIO list error: {e}")
            return []


# Singleton instance
minio_storage = MinIOStorage()
