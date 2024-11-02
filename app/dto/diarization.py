from datetime import datetime
from typing import List
from uuid import UUID
from pydantic import BaseModel, Field

class SpeechSegment(BaseModel):
    """Domain model for a speech segment."""
    start: float
    end: float
    speaker: str
    chunk_sequence: int = Field(..., description="Sequence number of the chunk")
    text: str = ""

class DiarizationResponse(BaseModel):
    """API response model."""
    session_id: UUID
    segments: List[SpeechSegment]
    total_speakers: int
    duration: float
    created_at: datetime
    is_complete: bool
    
    
class SummerizationResponse(BaseModel):
    session_id: UUID
    summary: str
    duration: float
    created_at: datetime
    is_complete: bool
    