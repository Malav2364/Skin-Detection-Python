"""
Capture service with business logic for upload and processing
"""

from sqlalchemy.orm import Session
from fastapi import UploadFile
from typing import Optional, List, Dict
from datetime import datetime
import uuid
import logging
from PIL import Image
import io

from db import (
    Capture, CaptureMetrics, Artifact, UserAdjustment,
    CaptureStatus, CaptureSource, ArtifactType, AdjustmentSource, User
)
from app.capture.schemas import (
    CaptureUploadMetadata, MetricsOnlyUpload,
    BodyMetrics, MetricsAdjustment
)
from app.storage import get_minio_client

logger = logging.getLogger(__name__)


class CaptureService:
    """Service for capture operations"""
    
    @staticmethod
    def strip_exif(image_bytes: bytes) -> bytes:
        """Strip EXIF metadata from image"""
        try:
            image = Image.open(io.BytesIO(image_bytes))
            
            # Create new image without EXIF
            data = list(image.getdata())
            image_without_exif = Image.new(image.mode, image.size)
            image_without_exif.putdata(data)
            
            # Save to bytes
            output = io.BytesIO()
            image_without_exif.save(output, format=image.format or 'JPEG')
            return output.getvalue()
        
        except Exception as e:
            logger.error(f"Error stripping EXIF: {str(e)}")
            # Return original if stripping fails
            return image_bytes
    
    @staticmethod
    def validate_image(file: UploadFile) -> bool:
        """Validate uploaded image"""
        # Check file size (max 50MB)
        MAX_SIZE = 50 * 1024 * 1024
        
        # Check content type
        allowed_types = ['image/jpeg', 'image/jpg', 'image/png']
        if file.content_type not in allowed_types:
            raise ValueError(f"Invalid file type: {file.content_type}")
        
        # Read file
        contents = file.file.read()
        file.file.seek(0)  # Reset file pointer
        
        if len(contents) > MAX_SIZE:
            raise ValueError(f"File too large: {len(contents)} bytes")
        
        # Validate it's actually an image
        try:
            Image.open(io.BytesIO(contents))
        except Exception as e:
            raise ValueError(f"Invalid image file: {str(e)}")
        
        return True
    
    @staticmethod
    def create_capture_from_images(
        db: Session,
        user: User,
        metadata: CaptureUploadMetadata,
        front_image: Optional[UploadFile] = None,
        side_image: Optional[UploadFile] = None,
        portrait_image: Optional[UploadFile] = None,
        reference_image: Optional[UploadFile] = None
    ) -> Capture:
        """Create capture from uploaded images"""
        
        # Validate images
        images = {
            'front': front_image,
            'side': side_image,
            'portrait': portrait_image,
            'reference': reference_image
        }
        
        for name, img in images.items():
            if img:
                CaptureService.validate_image(img)
        
        # Create capture record
        capture = Capture(
            id=uuid.uuid4(),
            user_id=user.id,
            status=CaptureStatus.QUEUED,
            source=CaptureSource(metadata.source.value),
            store_images=metadata.store_images
        )
        
        db.add(capture)
        db.commit()
        db.refresh(capture)
        
        # Upload images to MinIO if consent given
        if metadata.store_images:
            minio_client = get_minio_client()
            
            for name, img in images.items():
                if img:
                    # Read and strip EXIF
                    contents = img.file.read()
                    img.file.seek(0)
                    clean_contents = CaptureService.strip_exif(contents)
                    
                    # Upload to MinIO
                    object_name = f"{capture.id}/{name}.jpg"
                    bucket_path = minio_client.upload_bytes(
                        'raw',
                        object_name,
                        clean_contents,
                        content_type='image/jpeg'
                    )
                    
                    # Create artifact record
                    artifact = Artifact(
                        id=uuid.uuid4(),
                        capture_id=capture.id,
                        bucket_path=bucket_path,
                        artifact_type=ArtifactType.RAW,
                        file_size_bytes=len(clean_contents),
                        content_type='image/jpeg'
                    )
                    db.add(artifact)
            
            db.commit()
        
        logger.info(f"Created capture {capture.id} for user {user.email}")
        
        # Queue processing job
        from worker.tasks import process_capture
        process_capture.delay(str(capture.id))
        
        return capture
    
    @staticmethod
    def create_capture_from_metrics(
        db: Session,
        user: User,
        metrics_data: MetricsOnlyUpload
    ) -> Capture:
        """Create capture from client-side processed metrics"""
        
        # Create capture record
        capture = Capture(
            id=uuid.uuid4(),
            user_id=user.id,
            status=CaptureStatus.DONE,  # Already processed client-side
            source=CaptureSource(metrics_data.capture_meta.source.value),
            store_images=False
        )
        
        db.add(capture)
        db.flush()
        
        # Create metrics record
        metrics = CaptureMetrics(
            id=uuid.uuid4(),
            capture_id=capture.id,
            metrics_json={
                'original': metrics_data.metrics.dict(),
                'current': metrics_data.metrics.dict()
            },
            skin_json=metrics_data.skin.dict() if metrics_data.skin else None,
            shape_json=metrics_data.shape.dict() if metrics_data.shape else None,
            quality_json=metrics_data.quality.dict() if metrics_data.quality else None,
            model_versions={'client': 'web-v1.0'}  # Client-side version
        )
        
        db.add(metrics)
        db.commit()
        db.refresh(capture)
        
        logger.info(f"Created metrics-only capture {capture.id} for user {user.email}")
        
        return capture
    
    @staticmethod
    def get_capture_status(db: Session, capture_id: uuid.UUID, user: User) -> Capture:
        """Get capture status"""
        capture = db.query(Capture).filter(
            Capture.id == capture_id,
            Capture.user_id == user.id
        ).first()
        
        if not capture:
            raise ValueError("Capture not found")
        
        return capture
    
    @staticmethod
    def get_capture_results(db: Session, capture_id: uuid.UUID, user: User) -> Dict:
        """Get capture results"""
        capture = db.query(Capture).filter(
            Capture.id == capture_id,
            Capture.user_id == user.id
        ).first()
        
        if not capture:
            raise ValueError("Capture not found")
        
        if capture.status != CaptureStatus.DONE:
            raise ValueError(f"Capture not ready. Current status: {capture.status.value}")
        
        # Get metrics
        metrics = db.query(CaptureMetrics).filter(
            CaptureMetrics.capture_id == capture_id
        ).first()
        
        if not metrics:
            raise ValueError("Metrics not found")
        
        # Check for adjustments
        has_adjustments = db.query(UserAdjustment).filter(
            UserAdjustment.capture_id == capture_id
        ).count() > 0
        
        return {
            'capture_id': capture.id,
            'user_id': capture.user_id,
            'timestamp': capture.created_at,
            'metrics': metrics.metrics_json.get('current', {}),
            'skin': metrics.skin_json,
            'shape': metrics.shape_json,
            'quality': metrics.quality_json,
            'model_versions': metrics.model_versions,
            'has_adjustments': has_adjustments
        }
    
    @staticmethod
    def submit_adjustment(
        db: Session,
        capture_id: uuid.UUID,
        user: User,
        adjustment_data: MetricsAdjustment
    ) -> UserAdjustment:
        """Submit user adjustment to metrics"""
        
        # Get capture and verify ownership
        capture = db.query(Capture).filter(
            Capture.id == capture_id,
            Capture.user_id == user.id
        ).first()
        
        if not capture:
            raise ValueError("Capture not found")
        
        # Get current metrics
        metrics = db.query(CaptureMetrics).filter(
            CaptureMetrics.capture_id == capture_id
        ).first()
        
        if not metrics:
            raise ValueError("Metrics not found")
        
        # Create adjustment record
        adjustment = UserAdjustment(
            id=uuid.uuid4(),
            capture_id=capture_id,
            user_id=user.id,
            original_metrics_json=metrics.metrics_json.get('current', {}),
            adjusted_metrics_json=adjustment_data.adjusted_metrics.dict(),
            notes=adjustment_data.notes,
            source=AdjustmentSource(adjustment_data.source)
        )
        
        db.add(adjustment)
        
        # Update metrics to point to latest adjustment
        metrics.latest_adjustment_id = adjustment.id
        metrics.metrics_json['current'] = adjustment_data.adjusted_metrics.dict()
        
        # Lower confidence after user edit
        if metrics.quality_json:
            metrics.quality_json['overall_confidence'] *= 0.8
        
        # Update capture status
        capture.status = CaptureStatus.EDITED
        
        db.commit()
        db.refresh(adjustment)
        
        logger.info(f"User {user.email} submitted adjustment for capture {capture_id}")
        
        return adjustment
    
    @staticmethod
    def get_adjustment_history(
        db: Session,
        capture_id: uuid.UUID,
        user: User
    ) -> Dict:
        """Get adjustment history for a capture"""
        
        # Verify ownership
        capture = db.query(Capture).filter(
            Capture.id == capture_id,
            Capture.user_id == user.id
        ).first()
        
        if not capture:
            raise ValueError("Capture not found")
        
        # Get metrics
        metrics = db.query(CaptureMetrics).filter(
            CaptureMetrics.capture_id == capture_id
        ).first()
        
        if not metrics:
            raise ValueError("Metrics not found")
        
        # Get all adjustments
        adjustments = db.query(UserAdjustment).filter(
            UserAdjustment.capture_id == capture_id
        ).order_by(UserAdjustment.created_at).all()
        
        return {
            'capture_id': capture_id,
            'original_metrics': metrics.metrics_json.get('original', {}),
            'current_metrics': metrics.metrics_json.get('current', {}),
            'adjustments': adjustments
        }
