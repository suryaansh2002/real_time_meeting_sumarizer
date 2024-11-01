from uuid import UUID
import logging
from pydantic import UUID4

from fastapi import APIRouter, Depends, HTTPException, File, Form, UploadFile
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from app.dependencies.meetings import get_diarization_service, session_repository
from app.dto.meetings import AudioChunckBody, SessionStatus
from app.dto.diarization import DiarizationResponse
from app.repository.meetings.abstractions import AudioRepository
from app.services.diarization import StreamingDiarizationService

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/audio", tags=["movies"])

    
@router.post("/upload")
async def stream_diarize_audio(
    audio_file: UploadFile = File(...),
    session_id: UUID4 = Form(...),
    sequence_number: int = Form(...),
    is_final: bool = Form(...),
    service: StreamingDiarizationService = Depends(get_diarization_service)
):
    try:
        return await service.process_audio_chunk(
            audio_file.file,
            session_id,
            sequence_number,
            is_final
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error during streaming diarization: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")
    
   
@router.get("/session/{session_id}", response_model=DiarizationResponse)
async def get_session_diarization(
    session_id: UUID,
    service: StreamingDiarizationService = Depends(get_diarization_service)
) -> DiarizationResponse:
    """
    Retrieve diarization results for a complete session.
    """
    result = await service.get_session_transcript(session_id)
    if not result:
        raise HTTPException(status_code=404, detail="Session not found")
    return result

@router.get("/session/{session_id}/status", response_model=SessionStatus)
async def get_session_status(
    session_id: UUID,
    repository: AudioRepository = Depends(session_repository)
) -> SessionStatus:
    """
    Get the current status of an audio processing session.
    """
    result = await repository.get_session_diarization(session_id)
    if not result:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return SessionStatus(
        session_id=result.session_id,
        chunks_received=len(result.chunks),
        total_duration=result.duration,
        is_completed=result.is_complete,
        created_at=result.created_at,
        last_updated=result.last_updated
    )