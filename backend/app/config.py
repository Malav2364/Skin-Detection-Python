"""
Application configuration using Pydantic Settings
"""

from pydantic_settings import BaseSettings
from pydantic import Field, validator
from typing import List, Union
import os


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # Application
    APP_NAME: str = "Fabric Quality Analysis"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"
    
    # Database
    DATABASE_URL: str = Field(..., description="PostgreSQL connection string")
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 10
    
    # MinIO Object Storage
    MINIO_ENDPOINT: str = Field(..., description="MinIO endpoint (host:port)")
    MINIO_ACCESS_KEY: str
    MINIO_SECRET_KEY: str
    MINIO_SECURE: bool = False
    MINIO_BUCKET_RAW: str = "raw-captures"
    MINIO_BUCKET_PROCESSED: str = "processed-artifacts"
    MINIO_BUCKET_MODELS: str = "models"
    MINIO_BUCKET_EXPORTS: str = "exports"
    
    # RabbitMQ / Celery
    RABBITMQ_URL: str = Field(..., description="RabbitMQ connection URL")
    CELERY_BROKER_URL: str = Field(..., description="Celery broker URL")
    CELERY_RESULT_BACKEND: str = Field(..., description="Celery result backend URL")
    REDIS_URL: str = Field(..., description="Redis connection URL")
    
    # JWT Authentication
    JWT_SECRET: str = Field(..., description="Secret key for JWT signing")
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # CORS
    CORS_ORIGINS: Union[str, List[str]] = Field(
        default='["http://localhost:3000", "http://localhost:8080", "null"]',
        description="Allowed CORS origins (JSON array or comma-separated)"
    )
    
    @validator("CORS_ORIGINS", pre=True)
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            if not v or v.strip() == "":
                return ["http://localhost:3000", "http://localhost:5173"]
            return [origin.strip() for origin in v.split(",")]
        return v
    
    # Model Configuration
    MODEL_MANIFEST_URL: str = Field(..., description="URL to models.json manifest")
    DEFAULT_INFERENCE_MODE: str = "client"  # client or server
    ENABLE_SERVER_INFERENCE: bool = False
    
    # Privacy & Retention
    DEFAULT_IMAGE_RETENTION_DAYS: int = 1
    TRAINING_DATA_RETENTION_DAYS: int = 365
    ENABLE_METRICS_ONLY_MODE: bool = True
    
    # Observability
    PROMETHEUS_PORT: int = 9090
    ENABLE_TRACING: bool = False
    JAEGER_ENDPOINT: str = "http://localhost:14268/api/traces"
    
    # Worker Configuration
    WORKER_CONCURRENCY: int = 4
    WORKER_MAX_TASKS_PER_CHILD: int = 100
    WORKER_PREFETCH_MULTIPLIER: int = 4
    
    # Security
    ENCRYPTION_KEY: str = Field(default="dev-encryption-key-change-in-prod-32bytes", description="32-byte encryption key for AES-256")
    ENABLE_AUDIT_LOGS: bool = True
    MAX_UPLOAD_SIZE_MB: int = 50
    
    # Feature Flags
    ENABLE_PARTNER_API: bool = True
    ENABLE_ADMIN_PORTAL: bool = True
    ENABLE_WEBHOOKS: bool = False
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# Global settings instance
settings: Settings = None


def get_settings() -> Settings:
    """Get application settings (singleton pattern)"""
    global settings
    if settings is None:
        settings = Settings()
    return settings


def init_settings() -> Settings:
    """Initialize settings (called at startup)"""
    global settings
    settings = Settings()
    return settings
