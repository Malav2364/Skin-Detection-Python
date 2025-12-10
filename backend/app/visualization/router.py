"""
Visualization API endpoints
"""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session
import logging

from app.dependencies import get_db, get_current_user
from app.visualization.service import VisualizationService
from db import User, Capture

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/capture", tags=["visualization"])


@router.get("/{capture_id}/visualize/pose")
async def get_pose_visualization(
    capture_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get pose keypoint visualization image
    
    Args:
        capture_id: Capture UUID
        current_user: Authenticated user
    
    Returns:
        JPEG image with pose keypoints overlaid
    """
    try:
        # Verify ownership
        capture = db.query(Capture).filter(
            Capture.id == capture_id,
            Capture.user_id == current_user.id
        ).first()
        
        if not capture:
            raise HTTPException(status_code=404, detail="Capture not found")
        
        # Generate visualization
        image_bytes = VisualizationService.generate_pose_visualization(db, capture_id)
        
        if not image_bytes:
            raise HTTPException(status_code=500, detail="Failed to generate visualization")
        
        # Return image
        return Response(
            content=image_bytes,
            media_type="image/jpeg",
            headers={
                "Cache-Control": "public, max-age=3600"  # Cache for 1 hour
            }
        )
    
    except ValueError as e:
        logger.error(f"Error generating pose visualization: {str(e)}")
        raise HTTPException(status_code=404, detail=str(e))
    
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to generate visualization")


@router.get("/{capture_id}/visualize/segmentation")
async def get_segmentation_visualization(
    capture_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get segmentation mask visualization image
    
    Args:
        capture_id: Capture UUID
        current_user: Authenticated user
    
    Returns:
        JPEG image with segmentation mask overlaid
    """
    try:
        # Verify ownership
        capture = db.query(Capture).filter(
            Capture.id == capture_id,
            Capture.user_id == current_user.id
        ).first()
        
        if not capture:
            raise HTTPException(status_code=404, detail="Capture not found")
        
        # Generate visualization
        image_bytes = VisualizationService.generate_segmentation_visualization(db, capture_id)
        
        if not image_bytes:
            raise HTTPException(status_code=500, detail="Failed to generate visualization")
        
        # Return image
        return Response(
            content=image_bytes,
            media_type="image/jpeg",
            headers={
                "Cache-Control": "public, max-age=3600"  # Cache for 1 hour
            }
        )
    
    except ValueError as e:
        logger.error(f"Error generating segmentation visualization: {str(e)}")
        raise HTTPException(status_code=404, detail=str(e))
    
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to generate visualization")
