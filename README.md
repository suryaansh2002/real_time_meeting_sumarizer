# Meeting Summarizer

## Overview

This project is a Chrome extension and FastAPI server that records audio from a browser tab, processes it for speaker diarization and transcription, and provides a summarized text output. The extension captures audio, sends it to the server for processing, and displays the summary in the browser.

## Project Structure

- `chrome_extension/`: Contains the Chrome extension code.
- `server/`: Contains the FastAPI server code.
- `.gitignore`: Specifies files and directories to be ignored by Git.
- `requirements.txt`: Lists Python dependencies for the server.

## Setup

### Prerequisites

- Python 3.8 or higher
- Node.js and npm
- Google Chrome browser

### Installation

1. **Clone the repository:**

   ```bash
   git clone https://github.com/MadhavWalia/project.git
   cd project
   ```

2. **Install server dependencies:**

   Navigate to the `server` directory and install Python dependencies:

   ```bash
   cd server
   pip install -r requirements.txt
   ```

## Running the Project

1. **Start the FastAPI server:**

   In the `server` directory, run:

   ```bash
   python main.py
   ```

   This will start the server on `http://127.0.0.1:8080`.

2. **Load the Chrome extension:**

   - Open Chrome and navigate to `chrome://extensions/`.
   - Enable "Developer mode" in the top right corner.
   - Click "Load unpacked" and select the `chrome_extension` directory.

3. **Use the extension:**

   - Click the extension icon in the Chrome toolbar to start recording.
   - Click again to stop recording and view the summary.

## Purpose

#### This project was built as part of the Final Project for CS5242 Neural Networks and Deep Learning Course at the National University of Singapore. AY 2024-25 Semester 1.

