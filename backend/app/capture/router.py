"""
Capture router with endpoints for upload, status, and results
"""

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import Optional
import uuid
import json
import logging

from db import get_db, User
from app.dependencies import get_current_active_user
from app.capture.schemas import (
    CaptureResponse,
    CaptureStatusResponse,
    CaptureResultsResponse,
    CaptureUploadMetadata,
    MetricsOnlyUpload,
    MetricsAdjustment,
    AdjustmentApproval,
    AdjustmentHistoryResponse
)
from app.capture.service import CaptureService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("", response_model=CaptureResponse, status_code=status.HTTP_201_CREATED)
async def upload_capture(
    # Image files (optional for metrics-only upload)
    front: Optional[UploadFile] = File(None),
    side: Optional[UploadFile] = File(None),
    portrait: Optional[UploadFile] = File(None),
    reference: Optional[UploadFile] = File(None),
    
    # Metadata and metrics (JSON string in form data)
    metadata: Optional[str] = Form(None),
    metrics: Optional[str] = Form(None),
    
    # Dependencies
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Upload capture - supports two modes:
    
    1. **Image Upload**: Upload raw images for server-side processing
       - Requires: front, side, portrait images
       - Optional: reference card image
       - Metadata: JSON with source, store_images flag
    
    2. **Metrics-Only**: Upload pre-computed metrics from client-side processing
       - Requires: metrics JSON with body measurements
       - Optional: skin, shape, quality metrics
    """
    
    try:
        # Parse metadata if provided
        upload_metadata = None
        if metadata:
            metadata_dict = json.loads(metadata)
            upload_metadata = CaptureUploadMetadata(**metadata_dict)
        
        # Mode 1: Metrics-only upload (client-side processing)
        if metrics and not any([front, side, portrait]):
            metrics_dict = json.loads(metrics)
            metrics_data = MetricsOnlyUpload(**metrics_dict)
            
            capture = CaptureService.create_capture_from_metrics(
                db, current_user, metrics_data
            )
            
            return CaptureResponse(
                capture_id=capture.id,
                status=capture.status,
                message="Metrics uploaded successfully"
            )
        
        # Mode 2: Image upload (server-side processing)
        elif any([front, side, portrait]):
            if not upload_metadata:
                upload_metadata = CaptureUploadMetadata()
            
            # Require at least front and side images
            if not front or not side:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Front and side images are required"
                )
            
            capture = CaptureService.create_capture_from_images(
                db, current_user, upload_metadata,
                front, side, portrait, reference
            )
            
            return CaptureResponse(
                capture_id=capture.id,
                status=capture.status,
                message="Images uploaded successfully. Processing queued.",
                queue_position=None  # TODO: Get actual queue position
            )
        
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Either provide images or metrics data"
            )
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error uploading capture: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error processing upload"
        )


@router.get("/{capture_id}/status", response_model=CaptureStatusResponse)
async def get_capture_status(
    capture_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get processing status of a capture
    
    Returns current status, queue position, and progress information
    """
    try:
        capture = CaptureService.get_capture_status(db, capture_id, current_user)
        
        return CaptureStatusResponse(
            capture_id=capture.id,
            status=capture.status,
            queue_position=None,  # TODO: Calculate from queue
            progress=None,  # TODO: Get from worker
            current_stage=None,  # TODO: Get from worker
            error_message=capture.error_message,
            created_at=capture.created_at,
            processing_started_at=capture.processing_started_at,
            processing_completed_at=capture.processing_completed_at
        )
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.get("/{capture_id}/results", response_model=CaptureResultsResponse)
async def get_capture_results(
    capture_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get final results of a completed capture
    
    Returns all metrics, skin analysis, shape classification, and quality scores
    """
    try:
        results = CaptureService.get_capture_results(db, capture_id, current_user)
        return CaptureResultsResponse(**results)
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.patch("/{capture_id}/metrics", status_code=status.HTTP_200_OK)
async def submit_metrics_adjustment(
    capture_id: uuid.UUID,
    adjustment: MetricsAdjustment,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Submit user adjustments to metrics
    
    Allows users to correct or refine measurements
    """
    try:
        adjustment_record = CaptureService.submit_adjustment(
            db, capture_id, current_user, adjustment
        )
        
        return {
            "message": "Adjustment submitted successfully",
            "adjustment_id": adjustment_record.id,
            "status": "pending_approval"
        }
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.get("/{capture_id}/metrics/history", response_model=AdjustmentHistoryResponse)
async def get_metrics_history(
    capture_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get complete adjustment history for a capture
    
    Shows original metrics and all user adjustments
    """
    try:
        history = CaptureService.get_adjustment_history(db, capture_id, current_user)
        return AdjustmentHistoryResponse(**history)
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.post("/{capture_id}/adjustments/approve", status_code=status.HTTP_200_OK)
async def approve_adjustment(
    capture_id: uuid.UUID,
    approval: AdjustmentApproval,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Approve or reject a user adjustment (Admin/Tailor only)
    
    Requires elevated permissions
    """
    # TODO: Implement admin approval logic
    # For now, return not implemented
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Approval workflow not yet implemented"
    )
