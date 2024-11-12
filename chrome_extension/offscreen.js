let audioChunks = [];
let backendURL = 'http://127.0.0.1:8080/api/v1/audio/upload'; // FastAPI server URL

function generateUUID() {
  // Generates a valid UUID (v4)
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
    const r = Math.random() * 16 | 0, v = c === 'x' ? r : (r & 0x3 | 0x8);
    return v.toString(16);
  });
}

chrome.runtime.onMessage.addListener(async (message) => {
  if (message.target === 'offscreen') {
    switch (message.type) {
      case 'start-recording':
        startRecording(message.data);
        break;
      case 'stop-recording':
        stopRecording();
        break;
      default:
        throw new Error('Unrecognized message:', message.type);
    }
  }
});

let recorder;
let data = [];
let recordingSessionId; // Variable to hold unique session ID
let count = 0; // Sequence number for each chunk

async function startRecording(streamId) {
  if (recorder?.state === 'recording') {
    throw new Error('Called startRecording while recording is in progress.');
  }
  recordingSessionId = generateUUID(); // Use a valid UUID

  const media = await navigator.mediaDevices.getUserMedia({
    audio: {
      mandatory: {
        chromeMediaSource: 'tab',
        chromeMediaSourceId: streamId
      }
    }
  });

  // Continue to play the captured audio to the user.
  const output = new AudioContext();
  const source = output.createMediaStreamSource(media);
  source.connect(output.destination);

  // Start recording.
  recorder = new MediaRecorder(media, { mimeType: 'audio/webm' });
  recorder.ondataavailable = async (event) => {
    if (event.data.size > 0) {
      data.push(event.data);
      const blob = new Blob(data, { type: 'audio/webm' });
      const wavBlob = await convertWebmToWav(blob); // Convert to WAV format
      sendBlobToBackend(wavBlob, recordingSessionId, false); // `is_final` set to false for regular chunks
    }
  };
  
  recorder.onstop = async () => {
    // Send the last chunk of audio data with `is_final` set to true
    if (data.length > 0) {
      const blob = new Blob(data, { type: 'audio/webm' });
      const wavBlob = await convertWebmToWav(blob); // Convert to WAV format
      sendBlobToBackend(wavBlob, recordingSessionId, true); // `is_final` set to true for the last chunk
    }
    
    // Clear state ready for the next recording
    recorder = undefined;
    data = [];
    recordingSessionId = null; // Clear session ID for next recording
    count = 0; // Reset sequence number
  };

  recorder.start(30000); // Start recording with a time slice of 10 seconds

  window.location.hash = 'recording';
}

async function convertWebmToWav(blob) {
  // Use AudioContext to decode and convert audio to WAV format
  const audioContext = new AudioContext();
  const arrayBuffer = await blob.arrayBuffer();
  const audioBuffer = await audioContext.decodeAudioData(arrayBuffer);

  // Prepare WAV file data
  const wavBuffer = audioBufferToWav(audioBuffer);
  return new Blob([wavBuffer], { type: 'audio/wav' });
}

function audioBufferToWav(audioBuffer) {
  const numOfChannels = audioBuffer.numberOfChannels;
  const sampleRate = audioBuffer.sampleRate;
  const format = 1; // PCM
  const bitDepth = 16;

  // Calculate buffer size
  let samples = audioBuffer.length * numOfChannels;
  let buffer = new ArrayBuffer(44 + samples * 2);
  let view = new DataView(buffer);

  // Write WAV header
  writeString(view, 0, 'RIFF');
  view.setUint32(4, 36 + samples * 2, true);
  writeString(view, 8, 'WAVE');
  writeString(view, 12, 'fmt ');
  view.setUint32(16, 16, true);
  view.setUint16(20, format, true);
  view.setUint16(22, numOfChannels, true);
  view.setUint32(24, sampleRate, true);
  view.setUint32(28, sampleRate * numOfChannels * 2, true);
  view.setUint16(32, numOfChannels * 2, true);
  view.setUint16(34, bitDepth, true);
  writeString(view, 36, 'data');
  view.setUint32(40, samples * 2, true);

  // Write PCM samples
  let offset = 44;
  for (let i = 0; i < audioBuffer.numberOfChannels; i++) {
    let channel = audioBuffer.getChannelData(i);
    for (let j = 0; j < channel.length; j++) {
      view.setInt16(offset, channel[j] * 0x7FFF, true);
      offset += 2;
    }
  }

  return buffer;
}

function writeString(view, offset, string) {
  for (let i = 0; i < string.length; i++) {
    view.setUint8(offset + i, string.charCodeAt(i));
  }
}

async function sendBlobToBackend(blob, sessionId, isFinal) {
  try {
    const formData = new FormData();
    formData.append("audio_file", blob, `chunk${count}.wav`); // Send as WAV
    formData.append("session_id", sessionId);
    formData.append("sequence_number", count);
    formData.append("is_final", isFinal.toString());

    count++;

    const response = await fetch(backendURL, {
      method: "POST",
      body: formData
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`Error ${response.status}: ${errorText}`);
    }

    const responseData = await response.json();
    const messageString = responseData['summary'];
    chrome.runtime.sendMessage({ type: "message-update", messageString });
    console.log("Success:", responseData);

  } catch (error) {
    console.error("Error:", error);
  }
}

async function stopRecording() {
  recorder.stop();

  // Stopping the tracks makes sure the recording icon in the tab is removed.
  recorder.stream.getTracks().forEach((t) => t.stop());

  // Update current state in URL
  window.location.hash = '';
}
