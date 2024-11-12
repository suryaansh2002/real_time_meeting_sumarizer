// Initialize variables for letter-by-letter display
let letterIndex = 0;
let letterInterval; // Interval for letter display

// Function to display the next letter of the message string
function displayNextLetter(messageString) {
  const summaryElement = document.getElementById("summary");

  // Check if there are more letters in the message
  if (letterIndex < messageString.length) {
    summaryElement.appendChild(document.createTextNode(messageString[letterIndex])); // Append the next letter
    letterIndex++; // Move to the next letter
  } else {
    // When the entire message has been displayed, add BR elements for spacing
    clearInterval(letterInterval); // Stop the interval
    summaryElement.appendChild(document.createElement('BR')); // Line break
    summaryElement.appendChild(document.createElement('BR')); // Extra spacing

    // Reset letter index for the next message
    letterIndex = 0;
  }
}

// Function to start displaying letters of the received message string
function startLetterDisplay(messageString) {
  letterInterval = setInterval(() => displayNextLetter(messageString), 50); // Display letters every 50ms
}

// Listen for messages from the service worker
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === "display-message") {
    const summaryElement = document.getElementById("summary");
    summaryElement.textContent = ''; // Clear previous message

    // Start displaying letters of the new message
    startLetterDisplay(message.messageString);
  }
});
