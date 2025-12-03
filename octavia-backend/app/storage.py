"""File storage module for handling uploads (local/S3)."""
import os
import shutil
from pathlib import Path
from typing import Optional

# Storage configuration
STORAGE_TYPE = os.environ.get("STORAGE_TYPE", "local")  # 'local' or 's3'
UPLOAD_DIR = Path(os.environ.get("UPLOAD_DIR", "uploads"))

if STORAGE_TYPE == "local":
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def get_storage_path(user_id: str, file_type: str, filename: str) -> str:
    """Generate a unique storage path for a file."""
    return f"users/{user_id}/{file_type}/{filename}"


def save_upload_local(user_id: str, file_type: str, file_data: bytes, filename: str) -> str:
    """Save file to local storage. Returns storage path."""
    storage_path = get_storage_path(user_id, file_type, filename)
    full_path = UPLOAD_DIR / storage_path
    full_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(full_path, 'wb') as f:
        f.write(file_data)
    
    return storage_path


def get_file_local(storage_path: str) -> Optional[bytes]:
    """Retrieve file from local storage."""
    full_path = UPLOAD_DIR / storage_path
    if full_path.exists():
        with open(full_path, 'rb') as f:
            return f.read()
    return None


def delete_file_local(storage_path: str) -> bool:
    """Delete file from local storage."""
    full_path = UPLOAD_DIR / storage_path
    if full_path.exists():
        full_path.unlink()
        return True
    return False


def save_upload(user_id: str, file_type: str, file_data: bytes, filename: str) -> str:
    """Save uploaded file. Returns storage path."""
    if STORAGE_TYPE == "s3":
        # TODO: Implement S3 storage with boto3
        raise NotImplementedError("S3 storage not yet implemented")
    else:
        return save_upload_local(user_id, file_type, file_data, filename)


def get_file(storage_path: str) -> Optional[bytes]:
    """Retrieve file from storage."""
    if STORAGE_TYPE == "s3":
        # TODO: Implement S3 retrieval with boto3
        raise NotImplementedError("S3 storage not yet implemented")
    else:
        return get_file_local(storage_path)


def delete_file(storage_path: str) -> bool:
    """Delete file from storage."""
    if STORAGE_TYPE == "s3":
        # TODO: Implement S3 deletion with boto3
        raise NotImplementedError("S3 storage not yet implemented")
    else:
        return delete_file_local(storage_path)
