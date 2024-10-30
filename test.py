import requests
from uuid import uuid4
import wave
import io

def stream_audio_file(wav_file_path: str, chunk_size_seconds: float = 1.0):
    session_id = str(uuid4())
    url = "http://127.0.0.1:8080/api/v1/audio/upload"
    
    with wave.open(wav_file_path, 'rb') as wav_file:
        # Get file parameters
        framerate = wav_file.getframerate()
        chunk_size = int(framerate * chunk_size_seconds)
        
        sequence_number = 0
        while True:
            frames = wav_file.readframes(chunk_size)
            if not frames:
                break
                
            # Create a WAV file in memory
            wav_buffer = io.BytesIO()
            with wave.open(wav_buffer, 'wb') as chunk_wav:
                chunk_wav.setnchannels(wav_file.getnchannels())
                chunk_wav.setsampwidth(wav_file.getsampwidth())
                chunk_wav.setframerate(framerate)
                chunk_wav.writeframes(frames)
            
            # Prepare the request
            wav_buffer.seek(0)
            is_final = len(frames) < chunk_size
            
            files = {
                'audio_file': ('chunk.wav', wav_buffer, 'audio/wav')
            }
            
            data = {
                'session_id': session_id,
                'sequence_number': sequence_number,
                'is_final': str(is_final).lower()
            }
            
            # Send request
            try:
                response = requests.post(url, files=files, data=data)
                print(f"Chunk {sequence_number} - Status: {response.status_code}")
                if response.status_code != 200:
                    print(f"Error response: {response.text}")
            except Exception as e:
                print(f"Error sending chunk {sequence_number}: {str(e)}")
            
            sequence_number += 1

# Usage
stream_audio_file("test.wav", chunk_size_seconds=200.0)