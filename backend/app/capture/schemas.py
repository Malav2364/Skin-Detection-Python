"""
Pydantic schemas for capture upload and results
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, List
from datetime import datetime
from enum import Enum
import uuid


class CaptureSourceEnum(str, Enum):
    WEB = "web"
    MOBILE = "mobile"


class CaptureStatusEnum(str, Enum):
    QUEUED = "queued"
    PROCESSING = "processing"
    DONE = "done"
    FAILED = "failed"
    EDITED = "edited"


# Nested schemas for metrics
class BodyMetrics(BaseModel):
    """Body measurement metrics"""
    height_cm: Optional[float] = None
    shoulder_width_cm: Optional[float] = None
    chest_circumference_cm: Optional[float] = None
    waist_circumference_cm: Optional[float] = None
    hip_circumference_cm: Optional[float] = None
    inseam_cm: Optional[float] = None
    torso_length_cm: Optional[float] = None
    neck_circumference_cm: Optional[float] = None


class SkinMetrics(BaseModel):
    """Skin tone analysis metrics"""
    ita: Optional[float] = None
    lab: Optional[Dict[str, float]] = None  # L, a, b values
    monk_bucket: Optional[int] = Field(None, ge=1, le=10)
    undertone: Optional[str] = None  # warm, cool, neutral
    palette: Optional[List[Dict[str, str]]] = None  # [{hex, reason}]


class ShapeMetrics(BaseModel):
    """Body shape classification"""
    type: Optional[str] = None  # hourglass, rectangle, triangle, etc.
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0)


class QualityMetrics(BaseModel):
    """Quality assessment metrics"""
    lighting_ok: bool = True
    card_detected: bool = False
    overall_confidence: float = Field(0.0, ge=0.0, le=1.0)
    warnings: List[str] = Field(default_factory=list)


# Upload request schemas
class CaptureUploadMetadata(BaseModel):
    """Metadata for capture upload"""
    source: CaptureSourceEnum = CaptureSourceEnum.WEB
    store_images: bool = False
    device_info: Optional[Dict] = None


class MetricsOnlyUpload(BaseModel):
    """Schema for metrics-only upload (client-side processing)"""
    metrics: BodyMetrics
    skin: Optional[SkinMetrics] = None
    shape: Optional[ShapeMetrics] = None
    quality: Optional[QualityMetrics] = None
    capture_meta: CaptureUploadMetadata


# Response schemas
class CaptureResponse(BaseModel):
    """Response after capture upload"""
    capture_id: uuid.UUID
    status: CaptureStatusEnum
    message: str = "Capture uploaded successfully"
    queue_position: Optional[int] = None


class CaptureStatusResponse(BaseModel):
    """Response for status check"""
    capture_id: uuid.UUID
    status: CaptureStatusEnum
    queue_position: Optional[int] = None
    progress: Optional[float] = Field(None, ge=0.0, le=1.0)
    current_stage: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime
    processing_started_at: Optional[datetime] = None
    processing_completed_at: Optional[datetime] = None


class CaptureResultsResponse(BaseModel):
    """Complete results response"""
    capture_id: uuid.UUID
    user_id: uuid.UUID
    timestamp: datetime
    metrics: BodyMetrics
    skin: Optional[SkinMetrics] = None
    shape: Optional[ShapeMetrics] = None
    quality: Optional[QualityMetrics] = None
    model_versions: Dict[str, str] = Field(default_factory=dict)
    has_adjustments: bool = False
    
    class Config:
        from_attributes = True


# User adjustment schemas
class MetricsAdjustment(BaseModel):
    """User adjustment to metrics"""
    adjusted_metrics: BodyMetrics
    notes: Optional[str] = Field(None, max_length=500)
    source: str = "user"


class AdjustmentApproval(BaseModel):
    """Admin approval of adjustment"""
    adjustment_id: uuid.UUID
    approve: bool
    notes: Optional[str] = None


class AdjustmentHistoryItem(BaseModel):
    """Single adjustment history entry"""
    id: uuid.UUID
    user_id: uuid.UUID
    adjusted_metrics: BodyMetrics
    notes: Optional[str]
    source: str
    approved: bool
    approver_id: Optional[uuid.UUID]
    approved_at: Optional[datetime]
    created_at: datetime
    
    class Config:
        from_attributes = True


class AdjustmentHistoryResponse(BaseModel):
    """Complete adjustment history"""
    capture_id: uuid.UUID
    original_metrics: BodyMetrics
    current_metrics: BodyMetrics
    adjustments: List[AdjustmentHistoryItem]
