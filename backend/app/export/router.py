"""
Export API endpoints for generating and downloading reports
"""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session
from typing import Optional
import logging

from app.dependencies import get_db, get_current_user
from app.export.pdf_generator import PDFGenerator
from app.capture.service import CaptureService
from db import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/capture", tags=["export"])


@router.get("/{capture_id}/export/pdf")
async def export_pdf(
    capture_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Export capture results as PDF report
    
    Args:
        capture_id: UUID of the capture
        current_user: Authenticated user
    
    Returns:
        PDF file as download
    """
    try:
        # Get capture results
        results = CaptureService.get_capture_results(db, capture_id, current_user)
        
        # Generate PDF
        pdf_generator = PDFGenerator()
        pdf_bytes = pdf_generator.generate_report(results)
        
        # Return as downloadable PDF
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=report_{capture_id[:8]}.pdf"
            }
        )
    
    except ValueError as e:
        logger.error(f"Error exporting PDF for capture {capture_id}: {str(e)}")
        raise HTTPException(status_code=404, detail=str(e))
    
    except Exception as e:
        logger.error(f"Unexpected error exporting PDF: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to generate PDF report")


@router.get("/{capture_id}/export/json")
async def export_json(
    capture_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Export capture results as JSON
    
    Args:
        capture_id: UUID of the capture
        current_user: Authenticated user
    
    Returns:
        JSON data
    """
    try:
        # Get capture results
        results = CaptureService.get_capture_results(db, capture_id, current_user)
        
        return results
    
    except ValueError as e:
        logger.error(f"Error exporting JSON for capture {capture_id}: {str(e)}")
        raise HTTPException(status_code=404, detail=str(e))
    
    except Exception as e:
        logger.error(f"Unexpected error exporting JSON: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to export data")
