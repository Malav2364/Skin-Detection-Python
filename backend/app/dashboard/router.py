"""
Dashboard API endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
import logging

from app.dependencies import get_db, get_current_user
from app.dashboard.service import DashboardService
from db import User, CaptureStatus

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/user", tags=["dashboard"])


@router.get("/captures")
async def get_user_captures(
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get paginated list of user's captures
    
    Args:
        limit: Number of captures to return (1-100)
        offset: Offset for pagination
        status: Filter by status (queued, processing, done, failed)
        current_user: Authenticated user
    
    Returns:
        Paginated list of captures
    """
    try:
        # Parse status if provided
        status_filter = None
        if status:
            try:
                status_filter = CaptureStatus(status)
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid status: {status}. Must be one of: queued, processing, done, failed"
                )
        
        # Get captures
        result = DashboardService.get_user_captures(
            db,
            current_user,
            limit=limit,
            offset=offset,
            status=status_filter
        )
        
        return result
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching user captures: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch captures")


@router.get("/stats")
async def get_user_statistics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get user statistics
    
    Args:
        current_user: Authenticated user
    
    Returns:
        User statistics including total captures, status breakdown, and latest measurements
    """
    try:
        stats = DashboardService.get_user_statistics(db, current_user)
        return stats
    
    except Exception as e:
        logger.error(f"Error fetching user statistics: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch statistics")


@router.get("/history")
async def get_measurement_timeline(
    metric: str = Query("height_cm", description="Metric to track"),
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get measurement timeline for tracking changes
    
    Args:
        metric: Metric to track (e.g., height_cm, chest_circumference_cm)
        limit: Number of data points (1-50)
        current_user: Authenticated user
    
    Returns:
        Timeline of measurements
    """
    try:
        timeline = DashboardService.get_measurement_timeline(
            db,
            current_user,
            metric=metric,
            limit=limit
        )
        
        return {
            'metric': metric,
            'data_points': len(timeline),
            'timeline': timeline
        }
    
    except Exception as e:
        logger.error(f"Error fetching measurement timeline: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch timeline")


@router.get("/compare/{capture_id_1}/{capture_id_2}")
async def compare_captures(
    capture_id_1: str,
    capture_id_2: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Compare two captures side by side
    
    Args:
        capture_id_1: First capture ID
        capture_id_2: Second capture ID
        current_user: Authenticated user
    
    Returns:
        Comparison data with differences
    """
    try:
        comparison = DashboardService.compare_captures(
            db,
            current_user,
            capture_id_1,
            capture_id_2
        )
        
        return comparison
    
    except ValueError as e:
        logger.error(f"Error comparing captures: {str(e)}")
        raise HTTPException(status_code=404, detail=str(e))
    
    except Exception as e:
        logger.error(f"Unexpected error comparing captures: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to compare captures")
