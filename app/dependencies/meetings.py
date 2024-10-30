from functools import lru_cache
from fastapi import Depends
from app.repository.meetings.abstractions import AudioRepository
from app.repository.meetings.mongo import MongoAudioRepository
from app.services.diarization import StreamingDiarizationService
from app.services.knowledge_graph import KnowledgeGraphService
from app.services.summarize import SummarizationService
from app.settings.meetings import Settings, settings_instance


@lru_cache()
def session_repository(settings: Settings = Depends(settings_instance)):
    """
    Creates a singleton instance of Movie Repository Dependency
    """
    return MongoAudioRepository(
        connection_string=settings.mongo_connection_string,
        database_name=settings.mongo_database_name,
    )

@lru_cache()
def get_diarization_service(
    config: Settings = Depends(settings_instance),
    repository: AudioRepository = Depends(session_repository)
) -> StreamingDiarizationService:
    """Get diarization service instance."""
    return StreamingDiarizationService(config, repository)

@lru_cache()
def get_knowledge_graph_service() -> KnowledgeGraphService:
    """Get diarization service instance."""
    return KnowledgeGraphService()

@lru_cache()
def get_summerization_service(
    config: Settings = Depends(settings_instance),
    kb: KnowledgeGraphService = Depends(get_knowledge_graph_service)
) -> StreamingDiarizationService:
    """Get diarization service instance."""
    return SummarizationService(config, kb)