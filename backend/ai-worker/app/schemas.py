from pydantic import BaseModel
from typing import Optional

class JobUpdate(BaseModel):
    status: str
    result_url: Optional[str] = None
    error: Optional[str] = None
