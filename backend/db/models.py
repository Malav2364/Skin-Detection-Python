"""
Database schema for Fabric Quality Analysis System
"""

from sqlalchemy import (
    Column, String, Integer, Boolean, DateTime, Text, JSON, 
    ForeignKey, Enum, Index, Float
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
import enum

Base = declarative_base()


class UserRole(str, enum.Enum):
    USER = "user"
    ADMIN = "admin"
    LABELER = "labeler"
    PARTNER = "partner"


class CaptureStatus(str, enum.Enum):
    QUEUED = "queued"
    PROCESSING = "processing"
    DONE = "done"
    FAILED = "failed"
    EDITED = "edited"


class CaptureSource(str, enum.Enum):
    WEB = "web"
    MOBILE = "mobile"


class ArtifactType(str, enum.Enum):
    ALIGNED = "aligned"
    MASK = "mask"
    HEATMAP = "heatmap"
    RAW = "raw"


class AdjustmentSource(str, enum.Enum):
    USER = "user"
    TAILOR = "tailor"
    ADMIN = "admin"


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(Enum(UserRole), default=UserRole.USER, nullable=False)
    consent_flags = Column(JSONB, default={}, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_login = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)

    # Relationships
    captures = relationship("Capture", back_populates="user", cascade="all, delete-orphan")
    adjustments = relationship("UserAdjustment", back_populates="user")


class Capture(Base):
    __tablename__ = "captures"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    status = Column(Enum(CaptureStatus), default=CaptureStatus.QUEUED, nullable=False, index=True)
    source = Column(Enum(CaptureSource), default=CaptureSource.WEB, nullable=False)
    store_images = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    processing_started_at = Column(DateTime(timezone=True), nullable=True)
    processing_completed_at = Column(DateTime(timezone=True), nullable=True)
    error_message = Column(Text, nullable=True)

    # Relationships
    user = relationship("User", back_populates="captures")
    metrics = relationship("CaptureMetrics", back_populates="capture", uselist=False, cascade="all, delete-orphan")
    artifacts = relationship("Artifact", back_populates="capture", cascade="all, delete-orphan")
    labels = relationship("Label", back_populates="capture", cascade="all, delete-orphan")
    adjustments = relationship("UserAdjustment", back_populates="capture", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_user_status", "user_id", "status"),
        Index("idx_created_at", "created_at"),
    )


class CaptureMetrics(Base):
    __tablename__ = "capture_metrics"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    capture_id = Column(UUID(as_uuid=True), ForeignKey("captures.id", ondelete="CASCADE"), unique=True, nullable=False)
    
    # Metrics stored as JSONB for flexibility
    metrics_json = Column(JSONB, nullable=False)  # Contains: original, current, height, shoulder_width, etc.
    skin_json = Column(JSONB, nullable=True)  # ITA, LAB, Monk bucket, undertone, palette
    shape_json = Column(JSONB, nullable=True)  # Body shape type and confidence
    quality_json = Column(JSONB, nullable=True)  # Lighting, card detection, overall confidence
    
    # Model version tracking
    model_versions = Column(JSONB, default={}, nullable=False)  # {pose: "v1.2", regressor: "v2.0"}
    
    # Reference to latest adjustment
    latest_adjustment_id = Column(UUID(as_uuid=True), ForeignKey("user_adjustments.id"), nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    capture = relationship("Capture", back_populates="metrics")
    latest_adjustment = relationship("UserAdjustment", foreign_keys=[latest_adjustment_id], post_update=True)


class Artifact(Base):
    __tablename__ = "artifacts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    capture_id = Column(UUID(as_uuid=True), ForeignKey("captures.id", ondelete="CASCADE"), nullable=False, index=True)
    bucket_path = Column(String(512), nullable=False)  # MinIO bucket + object key
    artifact_type = Column(Enum(ArtifactType), nullable=False)
    file_size_bytes = Column(Integer, nullable=True)
    content_type = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    capture = relationship("Capture", back_populates="artifacts")

    __table_args__ = (
        Index("idx_capture_artifact_type", "capture_id", "artifact_type"),
    )


class Label(Base):
    __tablename__ = "labels"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    capture_id = Column(UUID(as_uuid=True), ForeignKey("captures.id", ondelete="CASCADE"), nullable=False, index=True)
    labeler_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    # Ground truth measurements
    measurements_json = Column(JSONB, nullable=False)
    
    approved = Column(Boolean, default=False, nullable=False)
    notes = Column(Text, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    approved_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    capture = relationship("Capture", back_populates="labels")
    labeler = relationship("User", foreign_keys=[labeler_id])


class UserAdjustment(Base):
    __tablename__ = "user_adjustments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    capture_id = Column(UUID(as_uuid=True), ForeignKey("captures.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    # Snapshot of original metrics before adjustment
    original_metrics_json = Column(JSONB, nullable=False)
    
    # User-supplied adjustments
    adjusted_metrics_json = Column(JSONB, nullable=False)
    
    # Context
    notes = Column(Text, nullable=True)
    source = Column(Enum(AdjustmentSource), default=AdjustmentSource.USER, nullable=False)
    
    # Approval workflow
    approved = Column(Boolean, default=False, nullable=False)
    approver_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    capture = relationship("Capture", back_populates="adjustments")
    user = relationship("User", back_populates="adjustments", foreign_keys=[user_id])
    approver = relationship("User", foreign_keys=[approver_id])

    __table_args__ = (
        Index("idx_capture_adjustments", "capture_id", "created_at"),
    )


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    actor_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)  # Nullable for system actions
    action = Column(String(100), nullable=False, index=True)  # e.g., "capture.upload", "user.delete"
    resource_type = Column(String(50), nullable=False)  # e.g., "capture", "user", "label"
    resource_id = Column(UUID(as_uuid=True), nullable=True)
    metadata = Column(JSONB, default={}, nullable=False)  # Additional context
    ip_address = Column(String(45), nullable=True)  # IPv4 or IPv6
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    # Relationships
    actor = relationship("User", foreign_keys=[actor_id])

    __table_args__ = (
        Index("idx_actor_action", "actor_id", "action"),
        Index("idx_resource", "resource_type", "resource_id"),
    )
