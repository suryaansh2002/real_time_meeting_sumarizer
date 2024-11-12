from typing import Dict, List, Optional, BinaryIO, Tuple
from datetime import datetime, timezone, timedelta
from uuid import UUID

import motor.motor_asyncio
from bson.objectid  import ObjectId
import gridfs
import logging

from pymongo import ASCENDING

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from app.dxo.meetings import AudioChunkDXO
from app.dxo.diarization import SessionDiarizationDXO

from app.repository.meetings.abstractions import RepositoryException, AudioRepository

class MongoAudioRepository(AudioRepository):
    """Repository for storing streaming diarization results and audio chunks in MongoDB."""
    
    def __init__(self, connection_string: str, database_name: str):
        self.client = motor.motor_asyncio.AsyncIOMotorClient(connection_string)
        self.db = self.client[database_name]
        self.fs_bucket = motor.motor_asyncio.AsyncIOMotorGridFSBucket(self.db)
        
    async def initialize(self):
        """Initialize database indexes."""
        try:
            # Create indexes for efficient querying
            await self.db.diarization_sessions.create_index("session_id", unique=True)
            await self.db.diarization_sessions.create_index("created_at")
            await self.db.diarization_sessions.create_index("is_complete")
            
            # Create indexes for GridFS metadata
            await self.db.fs_bucket.files.create_index("metadata.session_id")
            await self.db.fs_bucket.files.create_index([
                ("metadata.session_id", ASCENDING),
                ("metadata.sequence_number", ASCENDING)
            ])
            
            # Create index for chunks
            # chunks_collection = self.fs_bucket.chunks
            # await chunks_collection.create_index([
            #     ('files_id', ASCENDING),
            #     ('n', ASCENDING)
            # ], unique=True)
            
            logger.info("MongoDB indexes initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize MongoDB indexes: {str(e)}")
            raise RepositoryException(f"Failed to initialize MongoDB indexes: {str(e)}")
        
    async def store_audio_chunk(
        self,
        chunk: BinaryIO,
        chunk_dxo: AudioChunkDXO
    ) -> str:
        """Store a single audio chunk in GridFS."""
        try:
            file_content = chunk.read()
            chunk_id = str(ObjectId())
            
            await self.fs_bucket.upload_from_stream(
                f"{chunk_dxo.session_id}_{chunk_dxo.sequence_number}.wav",
                file_content,
                metadata={
                    "chunk_id": chunk_id,
                    "session_id": str(chunk_dxo.session_id),
                    "sequence_number": chunk_dxo.sequence_number,
                    "content_type": chunk_dxo.content_type,
                    "created_at": chunk_dxo.created_at,
                    "file_size": len(file_content)
                }
            )
            
            return chunk_id
            
        except Exception as e:
            logger.error(f"Failed to store audio chunk: {str(e)}")
            raise RepositoryException(f"Failed to store audio chunk: {str(e)}")

    async def update_session_diarization(
        self,
        session_dxo: SessionDiarizationDXO
    ) -> None:
        """Update or create session diarization results."""
        try:
            document = session_dxo.model_dump()
            document["session_id"] = str(document["session_id"]) 
            document["last_updated"] = datetime.now(timezone.utc)
            
            await self.db.diarization_sessions.update_one(
                {"session_id": str(session_dxo.session_id)},
                {"$set": document},
                upsert=True
            )
            
        except Exception as e:
            logger.error(f"Failed to update session diarization: {str(e)}")
            raise RepositoryException(f"Failed to update session diarization: {str(e)}")

    async def get_session_diarization(
        self,
        session_id: UUID
    ) -> Optional[SessionDiarizationDXO]:
        """Retrieve session diarization results."""
        try:
            result = await self.db.diarization_sessions.find_one(
                {"session_id": str(session_id)}
            )
            if not result:
                return None
                
            return SessionDiarizationDXO(**result)
            
        except Exception as e:
            logger.error(f"Failed to retrieve session diarization: {str(e)}")
            raise RepositoryException(f"Failed to retrieve session diarization: {str(e)}")

    async def get_session_chunks(
        self,
        session_id: UUID
    ) -> List[Tuple[int, bytes]]:
        """Retrieve all audio chunks for a session, ordered by sequence."""
        try:
            cursor = self.fs_bucket.find(
                {"metadata.session_id": str(session_id)},
                sort=[("metadata.sequence_number", 1)]
            )
            
            chunks = []
            async for grid_out in cursor:
                sequence = grid_out.metadata["sequence_number"]
                chunk_data = await grid_out.read()
                chunks.append((sequence, chunk_data))
                
            return chunks
            
        except Exception as e:
            logger.error(f"Failed to retrieve session chunks: {str(e)}")
            raise RepositoryException(f"Failed to retrieve session chunks: {str(e)}")

    async def delete_session(
        self,
        session_id: UUID
    ) -> bool:
        """Delete a complete session and its associated chunks."""
        try:
            # Start a transaction
            async with await self.client.start_session() as session:
                async with session.start_transaction():
                    # Delete session document
                    delete_result = await self.db.diarization_sessions.delete_one(
                        {"session_id": str(session_id)},
                        session=session
                    )
                    
                    # Delete all associated chunks
                    cursor = self.fs_bucket.find({"metadata.session_id": str(session_id)})
                    async for grid_out in cursor:
                        await self.fs_bucket.delete(grid_out._id, session=session)
                    
                    return delete_result.deleted_count > 0
                    
        except Exception as e:
            logger.error(f"Failed to delete session: {str(e)}")
            raise RepositoryException(f"Failed to delete session: {str(e)}")

    async def list_sessions(
        self,
        skip: int = 0,
        limit: int = 100,
        completed_only: bool = False
    ) -> List[SessionDiarizationDXO]:
        """List diarization sessions with pagination."""
        try:
            query = {"is_complete": True} if completed_only else {}
            cursor = self.db.diarization_sessions.find(query)\
                .sort("created_at", -1)\
                .skip(skip)\
                .limit(limit)
            
            return [SessionDiarizationDXO(**doc) async for doc in cursor]
            
        except Exception as e:
            logger.error(f"Failed to list sessions: {str(e)}")
            raise

    async def get_session_stats(
        self,
        session_id: UUID
    ) -> Dict:
        """Get detailed statistics for a session."""
        try:
            pipeline = [
                {"$match": {"metadata.session_id": str(session_id)}},
                {"$group": {
                    "_id": None,
                    "total_chunks": {"$sum": 1},
                    "total_size": {"$sum": "$metadata.file_size"},
                    "first_chunk": {"$min": "$metadata.created_at"},
                    "last_chunk": {"$max": "$metadata.created_at"}
                }}
            ]
            
            async for result in self.fs_bucket._files.aggregate(pipeline):
                return {
                    "total_chunks": result["total_chunks"],
                    "total_size_bytes": result["total_size"],
                    "duration_seconds": (result["last_chunk"] - result["first_chunk"]).total_seconds(),
                    "first_chunk_time": result["first_chunk"],
                    "last_chunk_time": result["last_chunk"]
                }
                
            return None
            
        except Exception as e:
            logger.error(f"Failed to get session stats: {str(e)}")
            raise

    async def cleanup_incomplete_sessions(
        self,
        older_than_hours: int = 24
    ) -> int:
        """Clean up incomplete sessions older than specified hours."""
        try:
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=older_than_hours)
            
            # Find incomplete sessions to delete
            sessions_to_delete = await self.db.diarization_sessions.find({
                "is_complete": False,
                "last_updated": {"$lt": cutoff_time}
            }).to_list(None)
            
            deleted_count = 0
            for session in sessions_to_delete:
                session_id = UUID(session["session_id"])
                if await self.delete_session(session_id):
                    deleted_count += 1
            
            return deleted_count
            
        except Exception as e:
            logger.error(f"Failed to cleanup incomplete sessions: {str(e)}")
            raise

    async def merge_session_chunks(
        self,
        session_id: UUID
    ) -> Optional[bytes]:
        """Merge all chunks of a completed session into a single audio file."""
        try:
            chunks = await self.get_session_chunks(session_id)
            if not chunks:
                return None
            
            # Merge WAV files maintaining headers only from first chunk
            result = chunks[0][1]  # First chunk with header
            for _, chunk_data in chunks[1:]:
                # Skip WAV header (44 bytes) for subsequent chunks
                result += chunk_data[44:]
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to merge session chunks: {str(e)}")
            raise

    async def close(self):
        """Close database connections."""
        try:
            await self.client.close()
            logger.info("MongoDB connections closed successfully")
        except Exception as e:
            logger.error(f"Error closing MongoDB connections: {str(e)}")
            raise