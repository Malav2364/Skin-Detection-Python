"""
Visualization service for generating pose and segmentation images
"""

from sqlalchemy.orm import Session
from io import BytesIO
from typing import Optional
import logging

from db import Capture, Artifact, ArtifactType
from app.storage import get_minio_client

logger = logging.getLogger(__name__)


class VisualizationService:
    """Service for generating visualization images"""
    
    @staticmethod
    def generate_pose_visualization(db: Session, capture_id: str) -> Optional[bytes]:
        """
        Generate pose keypoint visualization
        
        Args:
            db: Database session
            capture_id: Capture UUID
        
        Returns:
            JPEG image bytes or None
        """
        # Lazy imports to avoid loading heavy dependencies
        import cv2
        import numpy as np
        from models.pose_estimator import PoseEstimator
        
        try:
            # Get capture
            capture = db.query(Capture).filter(Capture.id == capture_id).first()
            if not capture:
                raise ValueError(f"Capture {capture_id} not found")
            
            # Get front view artifact
            artifact = db.query(Artifact).filter(
                Artifact.capture_id == capture_id,
                Artifact.artifact_type == ArtifactType.FRONT_VIEW
            ).first()
            
            if not artifact:
                raise ValueError("Front view image not found")
            
            # Download image from MinIO
            minio_client = get_minio_client()
            
            # Parse bucket path
            bucket_name, object_name = artifact.bucket_path.split('/', 1)
            
            # Map bucket name to type
            bucket_type_map = {
                'raw-captures': 'raw',
                'processed-captures': 'processed',
                'models': 'models'
            }
            bucket_type = bucket_type_map.get(bucket_name, 'raw')
            
            # Download image
            image_bytes = minio_client.download_file(bucket_type, object_name)
            
            # Convert to numpy array
            nparr = np.frombuffer(image_bytes, np.uint8)
            image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if image is None:
                raise ValueError("Failed to decode image")
            
            # Initialize pose estimator
            pose_estimator = PoseEstimator(
                min_detection_confidence=0.5,
                model_complexity=1
            )
            
            # Detect pose
            result = pose_estimator.detect(image)
            
            if result is None:
                logger.warning(f"No pose detected for capture {capture_id}")
                # Return original image
                _, buffer = cv2.imencode('.jpg', image)
                return buffer.tobytes()
            
            # Visualize
            annotated = pose_estimator.visualize(image, result['landmarks'])
            
            # Add text overlay
            h, w = annotated.shape[:2]
            cv2.putText(
                annotated,
                f"Keypoints: {len(result['landmarks'])} | Confidence: {result['confidence']:.1%}",
                (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 255, 0),
                2
            )
            
            # Encode to JPEG
            _, buffer = cv2.imencode('.jpg', annotated, [cv2.IMWRITE_JPEG_QUALITY, 90])
            
            logger.info(f"Generated pose visualization for capture {capture_id}")
            
            return buffer.tobytes()
        
        except Exception as e:
            logger.error(f"Error generating pose visualization: {str(e)}", exc_info=True)
            raise
    
    @staticmethod
    def generate_segmentation_visualization(db: Session, capture_id: str) -> Optional[bytes]:
        """
        Generate segmentation mask visualization
        
        Args:
            db: Database session
            capture_id: Capture UUID
        
        Returns:
            JPEG image bytes or None
        """
        # Lazy imports to avoid loading heavy dependencies
        import cv2
        import numpy as np
        from models.segmentation import SkinSegmenter
        
        try:
            # Get capture
            capture = db.query(Capture).filter(Capture.id == capture_id).first()
            if not capture:
                raise ValueError(f"Capture {capture_id} not found")
            
            # Get front view artifact
            artifact = db.query(Artifact).filter(
                Artifact.capture_id == capture_id,
                Artifact.artifact_type == ArtifactType.FRONT_VIEW
            ).first()
            
            if not artifact:
                raise ValueError("Front view image not found")
            
            # Download image from MinIO
            minio_client = get_minio_client()
            
            # Parse bucket path
            bucket_name, object_name = artifact.bucket_path.split('/', 1)
            
            # Map bucket name to type
            bucket_type_map = {
                'raw-captures': 'raw',
                'processed-captures': 'processed',
                'models': 'models'
            }
            bucket_type = bucket_type_map.get(bucket_name, 'raw')
            
            # Download image
            image_bytes = minio_client.download_file(bucket_type, object_name)
            
            # Convert to numpy array
            nparr = np.frombuffer(image_bytes, np.uint8)
            image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if image is None:
                raise ValueError("Failed to decode image")
            
            # Initialize segmenter
            segmenter = SkinSegmenter(model_selection=1)
            
            # Generate mask
            mask = segmenter.segment(image, threshold=0.5)
            
            person_pixels = int(np.sum(mask > 0))
            total_pixels = mask.shape[0] * mask.shape[1]
            percentage = (person_pixels / total_pixels) * 100
            
            # Visualize
            overlay = segmenter.visualize(image, mask)
            
            # Add text overlay
            cv2.putText(
                overlay,
                f"Person: {person_pixels:,} pixels ({percentage:.1f}%)",
                (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 255, 0),
                2
            )
            
            # Encode to JPEG
            _, buffer = cv2.imencode('.jpg', overlay, [cv2.IMWRITE_JPEG_QUALITY, 90])
            
            logger.info(f"Generated segmentation visualization for capture {capture_id}")
            
            return buffer.tobytes()
        
        except Exception as e:
            logger.error(f"Error generating segmentation visualization: {str(e)}", exc_info=True)
            raise
