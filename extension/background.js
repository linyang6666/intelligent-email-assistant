// background.js

// Ensure storage is initialized
chrome.runtime.onInstalled.addListener(() => {
  chrome.storage.local.get({ messages: [] }, () => {});
});

// Handle incoming messages
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  const { action, query } = request;

  if (action === 'getHistory') {
    // Return full messages array
    chrome.storage.local.get({ messages: [] }, data => {
      sendResponse({ history: data.messages });
    });
    return true; // async

  } else if (action === 'processQuestion') {
    // 1. Save user message
    chrome.storage.local.get({ messages: [] }, data => {
      data.messages.push({ sender: 'user', text: query });
      chrome.storage.local.set({ messages: data.messages });
    });

    // 2. Call your Flask endpoint
    fetch('http://127.0.0.1:5000/api//query', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query })
    })
      .then(r => r.json())
      .then(data => {
        const answer = data.answer || "Sorry, something went wrong.";

        // 3. Save bot reply
        chrome.storage.local.get({ messages: [] }, data2 => {
          data2.messages.push({ sender: 'bot', text: answer });
          chrome.storage.local.set({ messages: data2.messages });
        });

        // 4. Return reply to popup
        sendResponse({ answer });
      })
      .catch(_ => {
        const err = "Sorry, there was an error.";
        chrome.storage.local.get({ messages: [] }, data2 => {
          data2.messages.push({ sender: 'bot', text: err });
          chrome.storage.local.set({ messages: data2.messages });
        });
        sendResponse({ answer: err });
      });

    return true; // keep channel open
  }
});
