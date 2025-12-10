"""
Celery tasks for capture processing pipeline
"""

from celery import Task
from backend.worker.celery_app import celery_app
from sqlalchemy.orm import Session
import logging
import sys
import os
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from db import init_db, Capture, CaptureMetrics, CaptureStatus, Artifact, ArtifactType
from app.config import get_settings

logger = logging.getLogger(__name__)


class DatabaseTask(Task):
    """Base task with database session"""
    _db = None
    
    @property
    def db(self):
        if self._db is None:
            settings = get_settings()
            db_instance = init_db(
                settings.DATABASE_URL,
                pool_size=5,  # Smaller pool for workers
                max_overflow=10
            )
            self._db = db_instance
        return self._db


@celery_app.task(base=DatabaseTask, bind=True, max_retries=3)
def process_capture(self, capture_id: str):
    """
    Main task to process a capture through the complete pipeline
    
    Pipeline stages:
    1. Pre-check and validation
    2. Card detection + perspective correction
    3. Color calibration
    4. Pose & keypoint refinement
    5. Skin segmentation
    6. Skin metrics computation
    7. Width & depth extraction
    8. Circumference regression
    9. Post-processing & confidence scoring
    10. Persistence and notification
    """
    logger.info(f"Starting processing for capture {capture_id}")
    
    try:
        # Get database session
        with self.db.get_session() as db:
            # Get capture
            capture = db.query(Capture).filter(Capture.id == capture_id).first()
            if not capture:
                raise ValueError(f"Capture {capture_id} not found")
            
            # Update status to processing
            capture.status = CaptureStatus.PROCESSING
            capture.processing_started_at = datetime.utcnow()
            db.commit()
            
            # Get artifacts (images)
            from app.storage import get_minio_client
            from processing import (
                load_image_from_bytes, CardDetector, ColorCalibrator,
                SkinAnalyzer, resize_image
            )
            from processing.body_measurements import BodyMeasurements
            from models import ModelManager
            
            minio_client = get_minio_client()
            
            # Map bucket names to types (reverse of MinIO client's bucket mapping)
            bucket_name_to_type = {
                'raw-captures': 'raw',
                'processed-artifacts': 'processed',
                'models': 'models',
                'exports': 'exports'
            }
            
            artifacts = db.query(Artifact).filter(
                Artifact.capture_id == capture_id,
                Artifact.artifact_type == ArtifactType.RAW
            ).all()
            
            if not artifacts:
                raise ValueError("No images found for processing")
            
            # Load images
            images = {}
            for artifact in artifacts:
                # bucket_path format: "bucket-name/capture_id/image_name.jpg"
                bucket_name, object_name = artifact.bucket_path.split('/', 1)
                # Map bucket name to type for download
                bucket_type = bucket_name_to_type.get(bucket_name, 'raw')
                # Download using bucket type and full object path
                image_bytes = minio_client.download_file(bucket_type, object_name)
                # Extract image type from filename (front, side, portrait, reference)
                image_type = object_name.split('/')[-1].split('.')[0]
                images[image_type] = load_image_from_bytes(image_bytes)
            
            # Initialize processors
            card_detector = CardDetector()
            color_calibrator = ColorCalibrator()
            skin_analyzer = SkinAnalyzer()
            model_manager = ModelManager()
            
            # Stage 1-2: Card detection and color calibration
            logger.info(f"[{capture_id}] Stage 1-2: Card detection and calibration")
            scale = 10.0  # Default scale
            front_image = images.get('front')
            
            if 'reference' in images:
                card_result = card_detector.detect(images['reference'])
                if card_result:
                    scale = card_result['scale']
                    logger.info(f"Card detected, scale: {scale:.2f} px/cm")
                    
                    # Extract color patches and calibrate
                    patches = card_detector.extract_color_patches(card_result['corrected_image'])
                    if front_image is not None:
                        front_image = color_calibrator.calibrate(front_image, patches)
            else:
                # Apply gray world if no reference card
                if front_image is not None:
                    front_image = color_calibrator.apply_gray_world(front_image)
            
            # Stage 3-4: Pose estimation
            logger.info(f"[{capture_id}] Stage 3-4: Pose estimation")
            if front_image is not None:
                resized_front = resize_image(front_image, 512)
                keypoints = model_manager.predict_pose(resized_front)
                
                # Extract body measurements
                body_measurements = BodyMeasurements(pixels_per_cm=scale)
                measurements = body_measurements.extract_measurements(
                    keypoints, 
                    resized_front.shape[0]
                )
                pose_confidence = body_measurements.calculate_confidence(keypoints)
            else:
                raise ValueError("Front image required for processing")
            
            # Stage 5-6: Skin segmentation and analysis
            logger.info(f"[{capture_id}] Stage 5-6: Skin analysis")
            if 'portrait' in images:
                portrait = images['portrait']
                resized_portrait = resize_image(portrait, 512)
                
                # Get segmentation mask
                skin_mask = model_manager.predict_segmentation(resized_portrait)
                
                # Extract skin patches
                skin_patches = skin_analyzer.extract_skin_patches(
                    resized_portrait,
                    skin_mask,
                    regions=['face', 'neck']
                )
                
                # Analyze skin tone
                if skin_patches:
                    skin_results = skin_analyzer.analyze_multiple_patches(skin_patches)
                else:
                    skin_results = None
            else:
                skin_results = None
            
            # Stage 7-8: Circumference prediction
            logger.info(f"[{capture_id}] Stage 7-8: Circumference prediction")
            circumferences = model_manager.predict_circumferences(measurements)
            measurements.update(circumferences)
            
            # Stage 9: Confidence scoring
            logger.info(f"[{capture_id}] Stage 9: Confidence scoring")
            overall_confidence = pose_confidence * 0.8  # Weighted by pose confidence
            
            # Stage 10: Create metrics
            logger.info(f"[{capture_id}] Stage 10: Persisting results")
            metrics = CaptureMetrics(
                capture_id=capture.id,
                metrics_json={
                    'original': measurements,
                    'current': measurements
                },
                skin_json=skin_results if skin_results else {
                    'ita': None,
                    'lab': None,
                    'monk_bucket': None,
                    'undertone': None
                },
                shape_json={
                    'type': 'unknown',
                    'confidence': 0.0
                },
                quality_json={
                    'lighting_ok': True,
                    'card_detected': 'reference' in images,
                    'overall_confidence': float(overall_confidence),
                    'warnings': []
                },
                model_versions={
                    'pose': 'placeholder-v1.0',
                    'segmentation': 'placeholder-v1.0',
                    'regressor': 'placeholder-v1.0'
                }
            )
            
            db.add(metrics)
            
            # Update capture status
            capture.status = CaptureStatus.DONE
            capture.processing_completed_at = datetime.utcnow()
            
            db.commit()
            
            logger.info(f"Capture {capture_id} processed successfully")
            
            return {
                'capture_id': capture_id,
                'status': 'done',
                'message': 'Processing completed successfully'
            }
    
    except Exception as e:
        logger.error(f"Error processing capture {capture_id}: {str(e)}", exc_info=True)
        
        # Update capture status to failed
        try:
            with self.db.get_session() as db:
                capture = db.query(Capture).filter(Capture.id == capture_id).first()
                if capture:
                    capture.status = CaptureStatus.FAILED
                    capture.error_message = str(e)
                    db.commit()
        except Exception as db_error:
            logger.error(f"Error updating capture status: {str(db_error)}")
        
        # Retry the task
        raise self.retry(exc=e, countdown=60)


# Individual pipeline stage tasks (placeholders for Phase 2 implementation)

@celery_app.task(bind=True)
def task_validate_images(self, capture_id: str):
    """Stage 1: Validate images"""
    logger.info(f"[{capture_id}] Validating images")
    # TODO: Implement validation
    return {'stage': 'validate', 'status': 'success'}


@celery_app.task(bind=True)
def task_detect_card(self, capture_id: str):
    """Stage 2: Detect reference card"""
    logger.info(f"[{capture_id}] Detecting reference card")
    # TODO: Implement card detection
    return {'stage': 'card_detection', 'status': 'success'}


@celery_app.task(bind=True)
def task_color_calibration(self, capture_id: str):
    """Stage 3: Color calibration"""
    logger.info(f"[{capture_id}] Performing color calibration")
    # TODO: Implement color calibration
    return {'stage': 'color_calibration', 'status': 'success'}


@celery_app.task(bind=True)
def task_pose_keypoints(self, capture_id: str):
    """Stage 4: Pose and keypoint detection"""
    logger.info(f"[{capture_id}] Detecting pose and keypoints")
    # TODO: Implement pose detection
    return {'stage': 'pose_keypoints', 'status': 'success'}


@celery_app.task(bind=True)
def task_skin_segmentation(self, capture_id: str):
    """Stage 5: Skin segmentation"""
    logger.info(f"[{capture_id}] Performing skin segmentation")
    # TODO: Implement segmentation
    return {'stage': 'skin_segmentation', 'status': 'success'}


@celery_app.task(bind=True)
def task_skin_metrics(self, capture_id: str):
    """Stage 6: Compute skin metrics"""
    logger.info(f"[{capture_id}] Computing skin metrics")
    # TODO: Implement skin analysis
    return {'stage': 'skin_metrics', 'status': 'success'}


@celery_app.task(bind=True)
def task_body_measurements(self, capture_id: str):
    """Stage 7: Extract body measurements"""
    logger.info(f"[{capture_id}] Extracting body measurements")
    # TODO: Implement measurement extraction
    return {'stage': 'body_measurements', 'status': 'success'}


@celery_app.task(bind=True)
def task_circumference_regression(self, capture_id: str):
    """Stage 8: Predict circumferences"""
    logger.info(f"[{capture_id}] Predicting circumferences")
    # TODO: Implement regression
    return {'stage': 'circumference_regression', 'status': 'success'}


@celery_app.task(bind=True)
def task_confidence_scoring(self, capture_id: str):
    """Stage 9: Compute confidence scores"""
    logger.info(f"[{capture_id}] Computing confidence scores")
    # TODO: Implement confidence scoring
    return {'stage': 'confidence_scoring', 'status': 'success'}
