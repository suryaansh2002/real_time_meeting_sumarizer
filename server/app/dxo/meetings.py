from dataclasses import dataclass, field
from uuid import UUID
from pydantic import BaseModel
from datetime import datetime, timezone
    
@dataclass
class AudioChunkDXO:
    """Database exchange object for audio chunk metadata."""
    id: str
    session_id: UUID
    sequence_number: int
    original_filename: str
    content_type: str = "audio/wav"
    file_size: int = 0
    created_at: datetime = field(default_factory=datetime.utcnow)