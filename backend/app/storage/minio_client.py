"""
MinIO client wrapper for object storage
"""

from minio import Minio
from minio.error import S3Error
from typing import Optional, BinaryIO
from datetime import timedelta
import logging
import io

from app.config import get_settings

logger = logging.getLogger(__name__)


class MinIOClient:
    """Wrapper for MinIO operations"""
    
    def __init__(self):
        settings = get_settings()
        
        self.client = Minio(
            settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=settings.MINIO_SECURE
        )
        
        self.buckets = {
            "raw": settings.MINIO_BUCKET_RAW,
            "processed": settings.MINIO_BUCKET_PROCESSED,
            "models": settings.MINIO_BUCKET_MODELS,
            "exports": settings.MINIO_BUCKET_EXPORTS
        }
        
        # Initialize buckets
        self._init_buckets()
    
    def _init_buckets(self):
        """Create buckets if they don't exist"""
        for bucket_name in self.buckets.values():
            try:
                if not self.client.bucket_exists(bucket_name):
                    self.client.make_bucket(bucket_name)
                    logger.info(f"Created bucket: {bucket_name}")
                    
                    # TODO: Set lifecycle policies for retention
                    # TODO: Enable encryption at rest
            except S3Error as e:
                logger.error(f"Error initializing bucket {bucket_name}: {str(e)}")
    
    def upload_file(
        self,
        bucket_type: str,
        object_name: str,
        data: BinaryIO,
        length: int,
        content_type: str = "application/octet-stream",
        metadata: Optional[dict] = None
    ) -> str:
        """
        Upload a file to MinIO
        
        Args:
            bucket_type: Type of bucket (raw, processed, models, exports)
            object_name: Name/path of the object in the bucket
            data: File-like object containing the data
            length: Length of the data in bytes
            content_type: MIME type of the file
            metadata: Optional metadata dictionary
        
        Returns:
            Full bucket path (bucket/object_name)
        """
        bucket_name = self.buckets.get(bucket_type)
        if not bucket_name:
            raise ValueError(f"Invalid bucket type: {bucket_type}")
        
        try:
            self.client.put_object(
                bucket_name,
                object_name,
                data,
                length,
                content_type=content_type,
                metadata=metadata or {}
            )
            
            logger.info(f"Uploaded {object_name} to {bucket_name}")
            return f"{bucket_name}/{object_name}"
        
        except S3Error as e:
            logger.error(f"Error uploading {object_name}: {str(e)}")
            raise
    
    def upload_bytes(
        self,
        bucket_type: str,
        object_name: str,
        data: bytes,
        content_type: str = "application/octet-stream",
        metadata: Optional[dict] = None
    ) -> str:
        """Upload bytes data to MinIO"""
        data_stream = io.BytesIO(data)
        return self.upload_file(
            bucket_type,
            object_name,
            data_stream,
            len(data),
            content_type,
            metadata
        )
    
    def download_file(self, bucket_type: str, object_name: str) -> bytes:
        """
        Download a file from MinIO
        
        Args:
            bucket_type: Type of bucket
            object_name: Name/path of the object
        
        Returns:
            File contents as bytes
        """
        bucket_name = self.buckets.get(bucket_type)
        if not bucket_name:
            raise ValueError(f"Invalid bucket type: {bucket_type}")
        
        try:
            response = self.client.get_object(bucket_name, object_name)
            data = response.read()
            response.close()
            response.release_conn()
            
            logger.info(f"Downloaded {object_name} from {bucket_name}")
            return data
        
        except S3Error as e:
            logger.error(f"Error downloading {object_name}: {str(e)}")
            raise
    
    def get_presigned_url(
        self,
        bucket_type: str,
        object_name: str,
        expires: timedelta = timedelta(hours=1)
    ) -> str:
        """
        Generate a presigned URL for temporary access to an object
        
        Args:
            bucket_type: Type of bucket
            object_name: Name/path of the object
            expires: Expiration time for the URL
        
        Returns:
            Presigned URL string
        """
        bucket_name = self.buckets.get(bucket_type)
        if not bucket_name:
            raise ValueError(f"Invalid bucket type: {bucket_type}")
        
        try:
            url = self.client.presigned_get_object(
                bucket_name,
                object_name,
                expires=expires
            )
            
            logger.info(f"Generated presigned URL for {object_name}")
            return url
        
        except S3Error as e:
            logger.error(f"Error generating presigned URL: {str(e)}")
            raise
    
    def delete_file(self, bucket_type: str, object_name: str):
        """Delete a file from MinIO"""
        bucket_name = self.buckets.get(bucket_type)
        if not bucket_name:
            raise ValueError(f"Invalid bucket type: {bucket_type}")
        
        try:
            self.client.remove_object(bucket_name, object_name)
            logger.info(f"Deleted {object_name} from {bucket_name}")
        
        except S3Error as e:
            logger.error(f"Error deleting {object_name}: {str(e)}")
            raise
    
    def delete_files(self, bucket_type: str, object_names: list[str]):
        """Delete multiple files from MinIO"""
        bucket_name = self.buckets.get(bucket_type)
        if not bucket_name:
            raise ValueError(f"Invalid bucket type: {bucket_type}")
        
        try:
            for del_err in self.client.remove_objects(bucket_name, object_names):
                logger.error(f"Error deleting object: {del_err}")
            
            logger.info(f"Deleted {len(object_names)} objects from {bucket_name}")
        
        except S3Error as e:
            logger.error(f"Error in batch delete: {str(e)}")
            raise
    
    def file_exists(self, bucket_type: str, object_name: str) -> bool:
        """Check if a file exists in MinIO"""
        bucket_name = self.buckets.get(bucket_type)
        if not bucket_name:
            raise ValueError(f"Invalid bucket type: {bucket_type}")
        
        try:
            self.client.stat_object(bucket_name, object_name)
            return True
        except S3Error:
            return False


# Global MinIO client instance
minio_client: Optional[MinIOClient] = None


def get_minio_client() -> MinIOClient:
    """Get MinIO client instance (singleton)"""
    global minio_client
    if minio_client is None:
        minio_client = MinIOClient()
    return minio_client


def init_minio() -> MinIOClient:
    """Initialize MinIO client"""
    global minio_client
    minio_client = MinIOClient()
    return minio_client
