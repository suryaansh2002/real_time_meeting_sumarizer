import abc
from typing import BinaryIO, Dict, List, Optional, Tuple
from uuid import UUID

from app.dxo.diarization import SessionDiarizationDXO
from app.dxo.meetings import AudioChunkDXO

class RepositoryException(Exception):
    pass


class AudioRepository(abc.ABC):        
    async def initialize(self):
        """
        Initialize database indexes.
        
        """
        return NotImplementedError
        
    async def store_audio_chunk(
        self,
        chunk: BinaryIO,
        chunk_dxo: AudioChunkDXO
    ) -> str:
        """
        Store a single audio chunk in GridFS.
        
        """
        return NotImplementedError
    
    async def update_session_diarization(
        self,
        session_dxo: SessionDiarizationDXO
    ) -> None:
        """
        Update or create session diarization results.
        
        """
        return NotImplementedError

    async def get_session_diarization(
        self,
        session_id: UUID
    ) -> Optional[SessionDiarizationDXO]:
        """
        Retrieve session diarization results.
        
        """
        return NotImplementedError

    async def get_session_chunks(
        self,
        session_id: UUID
    ) -> List[Tuple[int, bytes]]:
        """
        Retrieve all audio chunks for a session, ordered by sequence.
        
        """
        return NotImplementedError

    async def delete_session(
        self,
        session_id: UUID
    ) -> bool:
        """
        Delete a complete session and its associated chunks.
        
        """
        return NotImplementedError

    async def list_sessions(
        self,
        skip: int = 0,
        limit: int = 100,
        completed_only: bool = False
    ) -> List[SessionDiarizationDXO]:
        """
        List diarization sessions with pagination.
        
        """
        return NotImplementedError

    async def get_session_stats(
        self,
        session_id: UUID
    ) -> Dict:
        """
        Get detailed statistics for a session.
        
        """
        return NotImplementedError

    async def cleanup_incomplete_sessions(
        self,
        older_than_hours: int = 24
    ) -> int:
        """
        Clean up incomplete sessions older than specified hours.
        
        """
        return NotImplementedError

    async def merge_session_chunks(
        self,
        session_id: UUID
    ) -> Optional[bytes]:
        """
        Merge all chunks of a completed session into a single audio file.
        
        """
        return NotImplementedError