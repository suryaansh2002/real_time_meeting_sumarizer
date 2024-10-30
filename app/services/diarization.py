import logging
import tempfile
from pathlib import Path
from typing import BinaryIO, List, Dict, Set, Tuple, Optional, Union
from uuid import UUID, uuid4
from bson.objectid  import ObjectId
from pyannote.audio import Pipeline
import torch
import whisper

from app.settings.meetings import Settings
from app.repository.meetings.abstractions import AudioRepository
from app.dto.diarization import SpeechSegment, DiarizationResponse

from app.dxo.diarization import SpeechSegmentDXO, SessionDiarizationDXO
from app.dxo.meetings import AudioChunkDXO


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

           
class StreamingDiarizationService:
    """Service handling streaming audio diarization logic."""
    
    def __init__(self, config: Settings, repository: AudioRepository):
        self.config = config
        self.repository = repository
        self.pipeline = self._initialize_pipeline()
        self.transcriber = self._initialize_transcriber()
        self.chunk_overlap_seconds = 0.5  # Overlap between chunks
        logger.info(f"Initialized diarization pipeline using device: {self.config.device}")
        
    def _initialize_pipeline(self) -> Pipeline:
        """Initialize the diarization pipeline with error handling."""
        try:
            print(self.config.hf_model_name, self.config.huggingface_auth_token)
            pipeline = Pipeline.from_pretrained(
                self.config.hf_model_name,
                use_auth_token=self.config.huggingface_auth_token
            )
            pipeline = pipeline.to(torch.device(self.config.device))
            return pipeline
        except Exception as e:
            logger.error(f"Failed to initialize pipeline: {str(e)}")
            raise RuntimeError(f"Failed to initialize pipeline: {str(e)}")
    
    def _initialize_transcriber(self) -> whisper.Whisper:
        """Initialize the Whisper transcription model."""
        try:
            model = whisper.load_model("base")
            return model.to(torch.device(self.config.device))
        except Exception as e:
            logger.error(f"Failed to initialize transcriber: {str(e)}")
            raise RuntimeError(f"Failed to initialize transcriber: {str(e)}")

    async def process_audio_chunk(
        self,
        chunk: BinaryIO,
        session_id: UUID,
        sequence_number: int,
        is_final: bool
    ) -> DiarizationResponse:
        """Process a single audio chunk and update session results."""
        temp_path = await self._save_temp_file(chunk)
        try:
            # Store the chunk
            chunk_dxo = AudioChunkDXO(
                id=str(ObjectId()),
                session_id=session_id,
                sequence_number=sequence_number,
                original_filename=f"{session_id}_{sequence_number}.wav"
            )
            chunk_id = await self.repository.store_audio_chunk(chunk, chunk_dxo)
            
            # Get existing session
            existing_dxo = await self.repository.get_session_diarization(session_id)
            
            # Process the current chunk
            segments, speakers, duration = await self._process_chunk(
                temp_path,
                sequence_number,
                existing_dxo
            )
            
            # Update session data
            session_dxo = await self._update_session_data(
                session_id=session_id,
                existing_dxo=existing_dxo,
                new_segments=segments,
                new_speakers=speakers,
                new_duration=duration,
                chunk_id=chunk_id,
                is_final=is_final
            )
            
            # If final chunk, perform post-processing
            if is_final:
                session_dxo = await self._finalize_session(session_dxo)
            
            return session_dxo.to_response()
            
        except Exception as e:
            logger.error(f"Processing failed: {str(e)}")
            raise ValueError(f"Failed to process audio chunk: {str(e)}")
        finally:
            self._cleanup_temp_file(temp_path)

    async def _process_chunk(
        self,
        audio_path: Path,
        sequence_number: int,
        existing_dxo: Optional[SessionDiarizationDXO]
    ) -> Tuple[List[SpeechSegment], Set[str], float]:
        """Process an audio chunk and return segments with transcription."""
        try:
            # Perform diarization
            diarization = self.pipeline(str(audio_path))
            
            # Perform transcription
            result = self.transcriber.transcribe(str(audio_path))
            
            segments = []
            speakers = set()
            max_end = 0.0
            
            # Process each speech turn and align with transcription
            for turn, _, speaker in diarization.itertracks(yield_label=True):
                speakers.add(speaker)
                
                # Adjust timing for sequence
                if existing_dxo and sequence_number > 0:
                    base_time = existing_dxo.duration - self.chunk_overlap_seconds
                else:
                    base_time = 0.0
                
                # Find corresponding transcription segment
                transcript_text = self._find_matching_transcript(
                    result["segments"],
                    base_time + turn.start,
                    base_time + turn.end
                )
                
                if transcript_text.strip():  # Only add segments with actual text
                    segment = SpeechSegment(
                        start=base_time + turn.start,
                        end=base_time + turn.end,
                        speaker=speaker,
                        chunk_sequence=sequence_number,
                        text=transcript_text
                    )
                    segments.append(segment)
                    max_end = max(max_end, segment.end)
            
            # If we have existing speakers, try to map new speakers to existing ones
            if existing_dxo and existing_dxo.segments:
                segments = self._map_speakers_to_existing(segments, existing_dxo.segments)
            
            return segments, speakers, max_end
            
        except Exception as e:
            logger.error(f"Failed to process chunk: {str(e)}")
            raise
    
    def _generate_conversation_transcript(
        self,
        segments: List[SpeechSegmentDXO]
    ) -> str:
        """Generate a conversational-style transcript."""
        current_speaker = None
        current_text_parts = []
        conversation_lines = []
        
        for segment in sorted(segments, key=lambda x: x.start):
            if segment.text.strip():  # Skip empty segments
                if segment.speaker != current_speaker:
                    # If we have accumulated text for the previous speaker, add it
                    if current_speaker and current_text_parts:
                        conversation_lines.append(
                            f"{current_speaker}: {' '.join(current_text_parts)}"
                        )
                        current_text_parts = []
                    
                    current_speaker = segment.speaker
                
                current_text_parts.append(segment.text.strip())
        
        # Add the last speaker's text if any
        if current_speaker and current_text_parts:
            conversation_lines.append(
                f"{current_speaker}: {' '.join(current_text_parts)}"
            )
        
        return "\n".join(conversation_lines)
    
    async def get_session_transcript(
        self,
        session_id: UUID,
        format: str = "text"
    ) -> Union[str, Dict]:
        """Generate a transcript of the diarization results."""
        try:
            session_dxo = await self.repository.get_session_diarization(session_id)
            if not session_dxo:
                raise ValueError("Session not found")
            
            if format == "text":
                return self._generate_conversation_transcript(session_dxo.segments)
            elif format == "json":
                return self._generate_json_transcript(session_dxo.segments)
            elif format == "detailed":
                return self._generate_text_transcript(session_dxo.segments)
            else:
                raise ValueError(f"Unsupported transcript format: {format}")
                
        except Exception as e:
            logger.error(f"Failed to generate transcript: {str(e)}")
            raise
    
    def _find_matching_transcript(
        self,
        transcript_segments: List[Dict],
        start_time: float,
        end_time: float
    ) -> str:
        """Find the transcribed text that corresponds to a given time segment."""
        matching_segments = []
        
        for segment in transcript_segments:
            segment_start = segment["start"]
            segment_end = segment["end"]
            
            # Check for overlap between segments
            if (segment_start <= end_time and segment_end >= start_time):
                matching_segments.append(segment["text"])
        
        return " ".join(matching_segments).strip()

    def _generate_text_transcript(
        self,
        segments: List[SpeechSegmentDXO]
    ) -> str:
        """Generate a detailed transcript with timestamps."""
        transcript_lines = []
        for segment in segments:
            if segment.text.strip():  # Skip empty segments
                timestamp = f"[{self._format_timestamp(segment.start)} - {self._format_timestamp(segment.end)}]"
                transcript_lines.append(f"{timestamp} {segment.speaker}: {segment.text}")
        return "\n".join(transcript_lines)

    def _generate_json_transcript(
        self,
        segments: List[SpeechSegmentDXO]
    ) -> Dict:
        """Generate a structured JSON transcript."""
        conversation = []
        current_speaker = None
        current_text_parts = []
        current_segment = None
        
        for segment in sorted(segments, key=lambda x: x.start):
            if segment.text.strip():  # Skip empty segments
                if segment.speaker != current_speaker:
                    # Add accumulated text for previous speaker
                    if current_speaker and current_text_parts:
                        conversation.append({
                            "speaker": current_speaker,
                            "text": " ".join(current_text_parts),
                            "start": current_segment.start,
                            "end": segment.start
                        })
                        current_text_parts = []
                    
                    current_speaker = segment.speaker
                    current_segment = segment
                
                current_text_parts.append(segment.text.strip())
        
        # Add the last speaker's text if any
        if current_speaker and current_text_parts:
            conversation.append({
                "speaker": current_speaker,
                "text": " ".join(current_text_parts),
                "start": current_segment.start,
                "end": segments[-1].end
            })
        
        return {"conversation": conversation}

    def _map_speakers_to_existing(
        self,
        new_segments: List[SpeechSegment],
        existing_segments: List[SpeechSegmentDXO]
    ) -> List[SpeechSegment]:
        """Map new speakers to existing ones based on temporal proximity."""
        try:
            # Get existing speaker mapping
            existing_speakers = {s.speaker for s in existing_segments}
            new_speakers = {s.speaker for s in new_segments}
            
            # If there's overlap in the first few segments, use that for mapping
            overlap_window = new_segments[:5]
            speaker_mapping = {}
            
            for new_segment in overlap_window:
                # Find temporally close existing segments
                close_segments = [
                    s for s in existing_segments
                    if abs(s.end - new_segment.start) < self.chunk_overlap_seconds
                ]
                
                if close_segments:
                    # Map to the closest existing speaker
                    closest_segment = min(
                        close_segments,
                        key=lambda s: abs(s.end - new_segment.start)
                    )
                    speaker_mapping[new_segment.speaker] = closest_segment.speaker
            
            # Apply mapping to all new segments
            mapped_segments = []
            for segment in new_segments:
                mapped_segment = segment.model_copy()
                if segment.speaker in speaker_mapping:
                    mapped_segment.speaker = speaker_mapping[segment.speaker]
                mapped_segments.append(mapped_segment)
            
            return mapped_segments
            
        except Exception as e:
            logger.error(f"Failed to map speakers: {str(e)}")
            raise

    async def _update_session_data(
        self,
        session_id: UUID,
        existing_dxo: Optional[SessionDiarizationDXO],
        new_segments: List[SpeechSegment],
        new_speakers: Set[str],
        new_duration: float,
        chunk_id: str,
        is_final: bool
    ) -> SessionDiarizationDXO:
        """Update session with new chunk data."""
        try:
            if existing_dxo:
                # Merge segments and update duration
                all_segments = list(existing_dxo.segments)
                all_segments.extend([SpeechSegmentDXO.from_domain(s) for s in new_segments])
                all_chunks = existing_dxo.chunks + [chunk_id]
                total_duration = max(existing_dxo.duration, new_duration)
            else:
                # Create new session data
                all_segments = [SpeechSegmentDXO.from_domain(s) for s in new_segments]
                all_chunks = [chunk_id]
                total_duration = new_duration
            
            # Create updated session DXO
            session_dxo = SessionDiarizationDXO.from_domain(
                entry_id=str(ObjectId()) if not existing_dxo else existing_dxo.id,
                session_id=session_id,
                chunks=all_chunks,
                segments=all_segments,
                total_speakers=len(set(s.speaker for s in all_segments)),
                duration=total_duration,
                is_complete=is_final
            )
            
            # Store updated session
            await self.repository.update_session_diarization(session_dxo)
            
            return session_dxo
            
        except Exception as e:
            logger.error(f"Failed to update session data: {str(e)}")
            raise

    async def _finalize_session(
        self,
        session_dxo: SessionDiarizationDXO
    ) -> SessionDiarizationDXO:
        """Perform final processing on a completed session."""
        try:
            # Merge overlapping segments
            merged_segments = self._merge_overlapping_segments(session_dxo.segments)
            
            # Normalize speaker labels
            normalized_segments = self._normalize_speaker_labels(merged_segments)
            
            # Create final session DXO
            final_dxo = SessionDiarizationDXO.from_domain(
                entry_id=session_dxo.id,
                session_id=session_dxo.session_id,
                chunks=session_dxo.chunks,
                segments=normalized_segments,
                total_speakers=len(set(s.speaker for s in normalized_segments)),
                duration=session_dxo.duration,
                is_complete=True
            )
            
            # Store final results
            await self.repository.update_session_diarization(final_dxo)
            
            return final_dxo
            
        except Exception as e:
            logger.error(f"Failed to finalize session: {str(e)}")
            raise

    def _merge_overlapping_segments(
        self,
        segments: List[SpeechSegmentDXO]
    ) -> List[SpeechSegmentDXO]:
        """Merge overlapping segments from the same speaker."""
        if not segments:
            return []
            
        # Sort segments by start time
        sorted_segments = sorted(segments, key=lambda x: (x.start, x.end))
        merged = []
        current = sorted_segments[0]
        
        for next_segment in sorted_segments[1:]:
            if (current.speaker == next_segment.speaker and 
                next_segment.start <= current.end + 0.1):  # Small tolerance
                # Merge segments
                current = SpeechSegmentDXO(
                    start=current.start,
                    end=max(current.end, next_segment.end),
                    speaker=current.speaker,
                    chunk_sequence=current.chunk_sequence,
                    text=current.text
                )
            else:
                merged.append(current)
                current = next_segment
        
        merged.append(current)
        return merged

    def _normalize_speaker_labels(
        self,
        segments: List[SpeechSegmentDXO]
    ) -> List[SpeechSegmentDXO]:
        """Normalize speaker labels to be sequential (SPEAKER_1, SPEAKER_2, etc.)."""
        try:
            # Create mapping of current labels to normalized ones
            unique_speakers = sorted(set(s.speaker for s in segments))
            speaker_mapping = {
                speaker: f"SPEAKER_{i+1}"
                for i, speaker in enumerate(unique_speakers)
            }
            
            # Apply mapping to all segments
            normalized_segments = []
            for segment in segments:
                normalized_segments.append(
                    SpeechSegmentDXO(
                        start=segment.start,
                        end=segment.end,
                        speaker=speaker_mapping[segment.speaker],
                        chunk_sequence=segment.chunk_sequence,
                        text=segment.text
                    )
                )
            
            return normalized_segments
            
        except Exception as e:
            logger.error(f"Failed to normalize speaker labels: {str(e)}")
            raise

    def _format_timestamp(self, seconds: float) -> str:
        """Format seconds into HH:MM:SS.mmm."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        seconds = seconds % 60
        return f"{hours:02d}:{minutes:02d}:{seconds:06.3f}"
            
    async def _save_temp_file(self, audio_data: BinaryIO) -> Path:
        """Save audio data to temporary file."""
        try:
            temp_dir = Path(tempfile.gettempdir()) / "diarization"
            temp_dir.mkdir(parents=True, exist_ok=True)
            
            temp_path = temp_dir / f"temp_{uuid4()}.wav"
            audio_content = audio_data.read()
            
            with open(temp_path, "wb") as f:
                f.write(audio_content)
            
            return temp_path
        except Exception as e:
            logger.error(f"Failed to save temporary file: {str(e)}")
            raise

    def _cleanup_temp_file(self, temp_path: Path) -> None:
        """Clean up temporary audio file."""
        try:
            if temp_path.exists():
                temp_path.unlink()
        except Exception as e:
            logger.error(f"Failed to cleanup temporary file: {str(e)}")