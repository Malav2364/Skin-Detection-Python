"""
Authentication service with JWT and password hashing
"""

from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from typing import Optional
import uuid
import logging

from db import User, UserRole
from app.config import get_settings
from app.auth.schemas import UserRegister, UserLogin

logger = logging.getLogger(__name__)

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AuthService:
    """Service for authentication operations"""
    
    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a password using bcrypt"""
        return pwd_context.hash(password)
    
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify a password against a hash"""
        return pwd_context.verify(plain_password, hashed_password)
    
    @staticmethod
    def create_access_token(user_id: uuid.UUID, expires_delta: Optional[timedelta] = None) -> str:
        """Create a JWT access token"""
        settings = get_settings()
        
        if expires_delta is None:
            expires_delta = timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
        
        expire = datetime.utcnow() + expires_delta
        
        to_encode = {
            "sub": str(user_id),
            "exp": expire,
            "type": "access"
        }
        
        encoded_jwt = jwt.encode(
            to_encode,
            settings.JWT_SECRET,
            algorithm=settings.JWT_ALGORITHM
        )
        
        return encoded_jwt
    
    @staticmethod
    def create_refresh_token(user_id: uuid.UUID, expires_delta: Optional[timedelta] = None) -> str:
        """Create a JWT refresh token"""
        settings = get_settings()
        
        if expires_delta is None:
            expires_delta = timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)
        
        expire = datetime.utcnow() + expires_delta
        
        to_encode = {
            "sub": str(user_id),
            "exp": expire,
            "type": "refresh"
        }
        
        encoded_jwt = jwt.encode(
            to_encode,
            settings.JWT_SECRET,
            algorithm=settings.JWT_ALGORITHM
        )
        
        return encoded_jwt
    
    @staticmethod
    def decode_token(token: str) -> dict:
        """Decode and validate a JWT token"""
        settings = get_settings()
        
        try:
            payload = jwt.decode(
                token,
                settings.JWT_SECRET,
                algorithms=[settings.JWT_ALGORITHM]
            )
            return payload
        except JWTError as e:
            logger.error(f"JWT decode error: {str(e)}")
            raise
    
    @staticmethod
    def register_user(db: Session, user_data: UserRegister) -> User:
        """Register a new user"""
        # Check if user already exists
        existing_user = db.query(User).filter(User.email == user_data.email).first()
        if existing_user:
            raise ValueError("Email already registered")
        
        # Create new user
        hashed_password = AuthService.hash_password(user_data.password)
        
        new_user = User(
            id=uuid.uuid4(),
            email=user_data.email,
            password_hash=hashed_password,
            role=UserRole.USER,
            consent_flags=user_data.consent_flags or {},
            is_active=True
        )
        
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        logger.info(f"New user registered: {user_data.email}")
        
        return new_user
    
    @staticmethod
    def authenticate_user(db: Session, login_data: UserLogin) -> Optional[User]:
        """Authenticate a user with email and password"""
        user = db.query(User).filter(User.email == login_data.email).first()
        
        if not user:
            logger.warning(f"Login attempt for non-existent user: {login_data.email}")
            return None
        
        if not AuthService.verify_password(login_data.password, user.password_hash):
            logger.warning(f"Failed login attempt for user: {login_data.email}")
            return None
        
        if not user.is_active:
            logger.warning(f"Login attempt for inactive user: {login_data.email}")
            return None
        
        # Update last login
        user.last_login = datetime.utcnow()
        db.commit()
        
        logger.info(f"User authenticated successfully: {login_data.email}")
        
        return user
    
    @staticmethod
    def change_password(db: Session, user: User, current_password: str, new_password: str) -> bool:
        """Change user password"""
        if not AuthService.verify_password(current_password, user.password_hash):
            logger.warning(f"Failed password change attempt for user: {user.email}")
            return False
        
        user.password_hash = AuthService.hash_password(new_password)
        db.commit()
        
        logger.info(f"Password changed for user: {user.email}")
        
        return True
    
    @staticmethod
    def update_consent_flags(db: Session, user: User, consent_flags: dict) -> User:
        """Update user consent flags"""
        user.consent_flags = consent_flags
        db.commit()
        db.refresh(user)
        
        logger.info(f"Consent flags updated for user: {user.email}")
        
        return user
