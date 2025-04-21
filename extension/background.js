// background.js - Chrome extension background service worker
chrome.runtime.onMessage.addListener(
  function(request, sender, sendResponse) {
    if (request.action === "processQuestion") {
      fetch('http://localhost:5000/api/query', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ query: request.query })
      })
      .then(response => response.json())
      .then(data => {
        sendResponse({ answer: data.answer });
      })
      .catch(error => {
        sendResponse({ answer: "Sorry, there was an error processing your request." });
      });
      return true;  // Indicates async response
    }
  }
);
