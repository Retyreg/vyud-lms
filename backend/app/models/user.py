from sqlalchemy import Column, Integer, String, Enum, Boolean, DateTime
from sqlalchemy.sql import func
import enum
from app.db.base import Base


class UserRole(str, enum.Enum):
    """RBAC roles as defined in the VYUD LMS spec (section 4.4)."""
    SUPER_ADMIN = "super_admin"       # HQ — full access, all regions
    REGIONAL_MANAGER = "regional_manager"  # manages a region
    STORE_MANAGER = "store_manager"   # manages a single location
    ASSOCIATE = "associate"           # frontline employee (Gen Z)
    # Legacy aliases kept for backward compatibility
    STUDENT = "student"
    CURATOR = "curator"
    ADMIN = "admin"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=True)
    role = Column(Enum(UserRole), default=UserRole.ASSOCIATE)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
