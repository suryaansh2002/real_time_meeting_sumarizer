# FastAPI Server for Meeting Summarizer

## Overview

This server processes audio data for speaker diarization and transcription using machine learning models. It provides an API for the Chrome extension to upload audio chunks and receive summarized text.

## Project Structure

- `app/`: Contains the main application code.
  - `services/`: Business logic for diarization and summarization.
  - `repository/`: Database interaction code.
  - `handlers/`: API route handlers.
  - `dto/`: Data transfer objects.
  - `dxo/`: Database exchange objects.
  - `settings/`: Configuration settings.
- `main.py`: Entry point for running the server.
- `requirements.txt`: Python dependencies.

## Setup

### Prerequisites

- Python 3.8 or higher
- MongoDB instance

### Installation

1. **Install dependencies:**

   ```bash
   pip install -r requirements.txt
   ```

2. **Configure environment variables:**

   Create a `.env` file in the `server` directory with the following variables:

   ```plaintext
   MONGO_CONNECTION_STRING=<your-mongo-connection-string>
   MONGO_DATABASE_NAME=<your-database-name>
   HF_MODEL_NAME=<huggingface-model-name>
   HUGGINGFACE_AUTH_TOKEN=<your-huggingface-auth-token>
   SM_MODEL_NAME=<summarization-model-name>
   ```

## Running the Server

Start the server using:

   ```bash
   python main.py
   ```



The server will run on `http://127.0.0.1:8080`.

## API Endpoints

- `POST /api/v1/audio/upload`: Upload audio chunks for processing.
- `GET /api/v1/audio/transcript`: Retrieve the transcript of a session.
