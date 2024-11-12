from datetime import datetime, timezone
from typing import List, Dict
from uuid import UUID
from pydantic import BaseModel, ConfigDict

from app.dto.diarization import SpeechSegment, DiarizationResponse

class SpeechSegmentDXO(BaseModel):
    """Database exchange object for speech segments."""
    start: float
    end: float
    speaker: str
    chunk_sequence: int
    text: str = ""

    model_config = ConfigDict(frozen=True)

    @classmethod
    def from_domain(cls, segment: SpeechSegment) -> "SpeechSegmentDXO":
        return cls(**segment.model_dump())

class SessionDiarizationDXO(BaseModel):
    """Database exchange object for session diarization results."""
    id: str
    session_id: UUID
    chunks: List[str]  # List of chunk IDs
    segments: List[SpeechSegmentDXO]
    total_speakers: int
    duration: float
    created_at: datetime
    last_updated: datetime
    is_complete: bool
    
    model_config = ConfigDict(frozen=True)
    
    @classmethod
    def from_domain(
        cls,
        entry_id: str,
        session_id: UUID,
        chunks: List[str],
        segments: List[SpeechSegment],
        total_speakers: int,
        duration: float,
        is_complete: bool
    ) -> "SessionDiarizationDXO":
        return cls(
            id=entry_id,
            session_id=session_id,
            chunks=chunks,
            segments=[SpeechSegmentDXO.from_domain(segment) for segment in segments],
            total_speakers=total_speakers,
            duration=duration,
            created_at=datetime.now(timezone.utc),
            last_updated=datetime.now(timezone.utc),
            is_complete=is_complete
        )
    
    def to_response(self) -> DiarizationResponse:
        """Convert DXO to API response model."""
        return DiarizationResponse(
            session_id=self.session_id,
            segments=[SpeechSegment(**segment.model_dump()) for segment in self.segments],
            total_speakers=self.total_speakers,
            duration=self.duration,
            created_at=self.created_at,
            is_complete=self.is_complete
        )