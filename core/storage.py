"""
MinIO Storage Service - Handle object storage for images
Vibe coding - plain mode: simple, direct, no over-engineering
"""
import os
import hashlib
import uuid
from datetime import timedelta
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
        """Initialize MinIO client (internal only for operations)"""
        # Internal client for Docker network (web container → minio container)
        self.client = Minio(
            settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=settings.MINIO_USE_SSL
        )
        
        self.bucket_products = settings.MINIO_BUCKET_PRODUCTS
        self.internal_endpoint = settings.MINIO_ENDPOINT
        self.external_endpoint = settings.MINIO_EXTERNAL_ENDPOINT
        
        # Ensure bucket exists (using internal client)
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
        Get direct URL for image access (no presigning - requires public bucket)
        
        Args:
            object_key: Object key in MinIO
            expires: Not used (kept for compatibility)
            
        Returns:
            str: Direct URL to MinIO object
        """
        # Return direct URL: http://localhost:9000/bucket/object_key
        # No signature needed if bucket is public or using anonymous access
        return f"http://{self.external_endpoint}/{self.bucket_products}/{object_key}"
    
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
    
    def download_image(self, object_key):
        """
        Download image binary data from MinIO
        
        Args:
            object_key: Object key in MinIO (e.g., "products/uuid/primary.jpg")
            
        Returns:
            bytes: Binary image data
            
        Raises:
            Exception: If download fails
        """
        try:
            response = self.client.get_object(
                bucket_name=self.bucket_products,
                object_name=object_key
            )
            
            # Read all data
            image_data = response.read()
            response.close()
            response.release_conn()
            
            return image_data
            
        except S3Error as e:
            print(f"✗ MinIO download error: {e}")
            raise Exception(f"Failed to download image: {str(e)}")
    
    def test_connection(self):
        """
        Test MinIO connection and return status
        
        Returns:
            dict: {
                'success': bool,
                'error': str (if failed),
                'details': dict (if success)
            }
        """
        try:
            # Try to list buckets
            buckets = self.client.list_buckets()
            bucket_names = [bucket.name for bucket in buckets]
            
            # Check if product bucket exists
            product_bucket_exists = self.bucket_products in bucket_names
            
            return {
                'success': True,
                'details': {
                    'endpoint': self.internal_endpoint,
                    'external_endpoint': self.external_endpoint,
                    'buckets': bucket_names,
                    'product_bucket': self.bucket_products,
                    'product_bucket_exists': product_bucket_exists,
                    'use_ssl': settings.MINIO_USE_SSL
                }
            }
            
        except S3Error as e:
            return {
                'success': False,
                'error': f"MinIO S3 Error: {str(e)}"
            }
        except Exception as e:
            return {
                'success': False,
                'error': f"Connection Error: {str(e)}"
            }


# Singleton instance
minio_storage = MinIOStorage()
