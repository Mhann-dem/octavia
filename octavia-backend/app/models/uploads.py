"""File upload models."""
import uuid
from sqlalchemy import Column, String, Integer, DateTime
from sqlalchemy.sql import func
from app.core.database import Base


class FileUpload(Base):
    """File upload record."""
    __tablename__ = "file_uploads"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), nullable=False, index=True)
    original_filename = Column(String, nullable=False)
    storage_path = Column(String, nullable=False)
    file_type = Column(String, nullable=False)  # 'video', 'audio', 'image'
    file_size = Column(Integer, nullable=False)  # In bytes
    created_at = Column(DateTime(timezone=True), server_default=func.now())
