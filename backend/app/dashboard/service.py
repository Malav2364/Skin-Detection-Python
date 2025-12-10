"""
Dashboard service for user statistics and capture management
"""

from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import logging

from db import Capture, User, CaptureStatus
from app.capture.service import CaptureService

logger = logging.getLogger(__name__)


class DashboardService:
    """Service for user dashboard operations"""
    
    @staticmethod
    def get_user_captures(
        db: Session,
        user: User,
        limit: int = 10,
        offset: int = 0,
        status: Optional[CaptureStatus] = None
    ) -> Dict[str, Any]:
        """
        Get paginated list of user's captures
        
        Args:
            db: Database session
            user: Current user
            limit: Number of captures to return
            offset: Offset for pagination
            status: Filter by status (optional)
        
        Returns:
            Dictionary with captures and pagination info
        """
        # Build query
        query = db.query(Capture).filter(Capture.user_id == user.id)
        
        # Filter by status if provided
        if status:
            query = query.filter(Capture.status == status)
        
        # Get total count
        total = query.count()
        
        # Get paginated results
        captures = query.order_by(desc(Capture.created_at)).limit(limit).offset(offset).all()
        
        # Format results
        capture_list = []
        for capture in captures:
            capture_list.append({
                'capture_id': str(capture.id),
                'status': capture.status.value,
                'source': capture.source.value if capture.source else None,
                'created_at': capture.created_at.isoformat(),
                'updated_at': capture.updated_at.isoformat() if capture.updated_at else None,
                'has_results': capture.status == CaptureStatus.DONE
            })
        
        return {
            'captures': capture_list,
            'total': total,
            'limit': limit,
            'offset': offset,
            'has_more': (offset + limit) < total
        }
    
    @staticmethod
    def get_user_statistics(db: Session, user: User) -> Dict[str, Any]:
        """
        Get user statistics
        
        Args:
            db: Database session
            user: Current user
        
        Returns:
            Dictionary with user statistics
        """
        # Total captures
        total_captures = db.query(Capture).filter(Capture.user_id == user.id).count()
        
        # Captures by status
        status_counts = db.query(
            Capture.status,
            func.count(Capture.id)
        ).filter(
            Capture.user_id == user.id
        ).group_by(Capture.status).all()
        
        status_breakdown = {status.value: count for status, count in status_counts}
        
        # Recent activity (last 30 days)
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        recent_captures = db.query(Capture).filter(
            Capture.user_id == user.id,
            Capture.created_at >= thirty_days_ago
        ).count()
        
        # Get latest measurements (from most recent completed capture)
        latest_capture = db.query(Capture).filter(
            Capture.user_id == user.id,
            Capture.status == CaptureStatus.DONE
        ).order_by(desc(Capture.created_at)).first()
        
        latest_measurements = None
        if latest_capture:
            try:
                results = CaptureService.get_capture_results(db, str(latest_capture.id), user)
                latest_measurements = {
                    'capture_id': str(latest_capture.id),
                    'date': latest_capture.created_at.isoformat(),
                    'metrics': results.get('metrics', {}),
                    'skin': results.get('skin', {})
                }
            except Exception as e:
                logger.warning(f"Could not fetch latest measurements: {str(e)}")
        
        return {
            'total_captures': total_captures,
            'status_breakdown': status_breakdown,
            'recent_captures_30d': recent_captures,
            'latest_measurements': latest_measurements,
            'member_since': user.created_at.isoformat()
        }
    
    @staticmethod
    def get_measurement_timeline(
        db: Session,
        user: User,
        metric: str = 'height_cm',
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get measurement timeline for a specific metric
        
        Args:
            db: Database session
            user: Current user
            metric: Metric to track (e.g., 'height_cm', 'chest_circumference_cm')
            limit: Number of data points
        
        Returns:
            List of measurement data points
        """
        # Get completed captures
        captures = db.query(Capture).filter(
            Capture.user_id == user.id,
            Capture.status == CaptureStatus.DONE
        ).order_by(desc(Capture.created_at)).limit(limit).all()
        
        timeline = []
        for capture in captures:
            try:
                results = CaptureService.get_capture_results(db, str(capture.id), user)
                metrics = results.get('metrics', {})
                
                if metric in metrics:
                    timeline.append({
                        'capture_id': str(capture.id),
                        'date': capture.created_at.isoformat(),
                        'value': metrics[metric],
                        'metric': metric
                    })
            except Exception as e:
                logger.warning(f"Could not fetch results for capture {capture.id}: {str(e)}")
                continue
        
        # Reverse to get chronological order
        timeline.reverse()
        
        return timeline
    
    @staticmethod
    def compare_captures(
        db: Session,
        user: User,
        capture_id_1: str,
        capture_id_2: str
    ) -> Dict[str, Any]:
        """
        Compare two captures side by side
        
        Args:
            db: Database session
            user: Current user
            capture_id_1: First capture ID
            capture_id_2: Second capture ID
        
        Returns:
            Comparison data
        """
        # Get both captures
        results_1 = CaptureService.get_capture_results(db, capture_id_1, user)
        results_2 = CaptureService.get_capture_results(db, capture_id_2, user)
        
        # Calculate differences
        metrics_1 = results_1.get('metrics', {})
        metrics_2 = results_2.get('metrics', {})
        
        differences = {}
        for key in metrics_1.keys():
            if key in metrics_2:
                diff = metrics_2[key] - metrics_1[key]
                percent_change = (diff / metrics_1[key] * 100) if metrics_1[key] != 0 else 0
                
                differences[key] = {
                    'value_1': metrics_1[key],
                    'value_2': metrics_2[key],
                    'difference': diff,
                    'percent_change': percent_change
                }
        
        return {
            'capture_1': {
                'id': capture_id_1,
                'date': results_1.get('timestamp'),
                'metrics': metrics_1,
                'skin': results_1.get('skin', {})
            },
            'capture_2': {
                'id': capture_id_2,
                'date': results_2.get('timestamp'),
                'metrics': metrics_2,
                'skin': results_2.get('skin', {})
            },
            'differences': differences
        }
