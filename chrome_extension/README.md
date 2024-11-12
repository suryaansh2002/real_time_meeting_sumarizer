# Chrome Extension for Meeting Summarizer

## Overview

This Chrome extension captures audio from the current tab, sends it to a FastAPI server for processing, and displays a summarized text output. It uses the Chrome `tabCapture` API to record audio and communicates with the server via HTTP requests.

## Project Structure

- `index.html`: Main HTML file for the extension's UI.
- `index.js`: JavaScript file for handling UI interactions and messaging.
- `offscreen.js`: Handles audio recording and communication with the server.
- `service-worker.js`: Background script for managing extension state.
- `manifest.json`: Extension configuration file.
- `index.css`: Styles for the extension UI.

## Setup

### Prerequisites

- Google Chrome browser

### Installation

1. **Load the extension in Chrome:**

   - Open Chrome and navigate to `chrome://extensions/`.
   - Enable "Developer mode" in the top right corner.
   - Click "Load unpacked" and select the `chrome_extension` directory.

## Usage

1. **Start recording:**

   Click the extension icon in the Chrome toolbar to start recording audio from the current tab.

2. **Stop recording:**

   Click the icon again to stop recording. The summarized text will be displayed in the extension popup.

