from datetime import datetime
from uuid import UUID
from fastapi import File, Form, UploadFile
from pydantic import BaseModel, field_validator

class AudioChunckBody(BaseModel):    
    """Input DTO for streaming audio session."""
    audio_file: UploadFile = File(..., description="WAV audio chunk")
    session_id: UUID = Form(..., description="Unique session identifier")
    sequence_number: int = Form(..., description="Chunk sequence number")
    is_final: bool = Form(False, description="Indicates if this is the final chunk")

    @field_validator('audio_file')
    @classmethod
    def validate_audio_file(cls, file: UploadFile) -> UploadFile:
        if not file.filename.lower().endswith('.wav'):
            raise ValueError("File must have .wav extension")
        
        file_content = file.file.read(44)
        file.file.seek(0)
        
        if not file_content.startswith(b'RIFF') or b'WAVE' not in file_content[:44]:
            raise ValueError("File must be a valid WAV audio file")
        
        return file

    model_config = {
        "arbitrary_types_allowed": True
    }
    

class SessionStatus(BaseModel):
    """Status information for an audio session."""
    session_id: UUID
    chunks_received: int
    total_duration: float
    is_completed: bool
    created_at: datetime
    last_updated: datetime