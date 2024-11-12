from uuid import UUID
import logging
from pydantic import UUID4

from fastapi import APIRouter, Depends, HTTPException, File, Form, UploadFile

from app.dependencies.meetings import get_diarization_service, get_summerization_service
from app.dto.diarization import SummerizationResponse
from app.services.diarization import StreamingDiarizationService
from app.services.summarize import SummarizationService

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/audio", tags=["movies"])

    
@router.post("/upload", response_model=SummerizationResponse)
async def stream_diarize_audio(
    audio_file: UploadFile = File(...),
    session_id: UUID4 = Form(...),
    sequence_number: int = Form(...),
    is_final: bool = Form(...),
    service: StreamingDiarizationService = Depends(get_diarization_service),
    sum_service: SummarizationService = Depends(get_summerization_service)
) -> SummerizationResponse:
    """
    Endpoint to process streaming audio chunks and perform speaker diarization.
    """
    try:
        dia_response =  await service.process_audio_chunk(
            audio_file.file,
            session_id,
            sequence_number,
            is_final
        )
        
        transcript = await service.get_session_transcript(session_id)
        
        summary = await sum_service.summerize(script=transcript)
        
        return SummerizationResponse(
            session_id=session_id,
            summary=summary,
            duration=dia_response.duration,
            created_at=dia_response.created_at,
            is_complete=dia_response.is_complete
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error during streaming diarization: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")