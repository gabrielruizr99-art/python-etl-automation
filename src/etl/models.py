from datetime import datetime

from pydantic import BaseModel, Field


class DiscoveredFile(BaseModel):
    file_name: str
    file_path: str
    file_hash: str = Field(..., pattern=r"^[a-fA-F0-9]{64}$")
    file_size_bytes: int = Field(..., ge=0)
    modified_at: datetime
    
    model_config = {"frozen": True}  # Modelo inmutable
