// popup.js

document.addEventListener('DOMContentLoaded', () => {
  const emailListEl    = document.getElementById('email-list');
  const chatContainer  = document.getElementById('chat-container');
  const userInput      = document.getElementById('user-input');
  const sendButton     = document.getElementById('send-button');
  const clearButton    = document.getElementById('clear-history');
  const WELCOME        = 'Hello! I can help answer questions about your emails. What would you like to know?';

  // Fetch & render emails (unchanged) …
  fetch('http://localhost:5006/api/emails')
    .then(res => res.json())
    .then(emails => {
      emailListEl.innerHTML = '<strong>Recent Emails:</strong>';
      emails.forEach(e => {
        const div = document.createElement('div');
        div.className = 'email-item';
        div.innerHTML = `
          <div class="subject">${e.subject}</div>
          <div class="from">From: ${e.sender}</div>
          <div class="snippet">${e.snippet}…</div>`;
        emailListEl.appendChild(div);
      });
    })
    .catch(_ => emailListEl.textContent = 'Failed to load emails.');

  // Load & render chat history
  chrome.runtime.sendMessage({ action: 'getHistory' }, resp => {
    const history = resp.history || [];
    chatContainer.innerHTML = '';
    if (history.length === 0) {
      addBubble('bot', WELCOME);
    } else {
      history.forEach(m => addBubble(m.sender, m.text));
    }
  });

  // Send button & Enter key
  sendButton.addEventListener('click', onSend);
  userInput.addEventListener('keypress', e => {
    if (e.key === 'Enter') onSend();
  });

  // Clear History button
  clearButton.addEventListener('click', () => {
    chrome.storage.local.set({ messages: [] }, () => {
      chatContainer.innerHTML = '';
      addBubble('bot', WELCOME);
    });
  });

  function onSend() {
    const text = userInput.value.trim();
    if (!text) return;
    userInput.value = '';

    addBubble('user', text);
    chrome.runtime.sendMessage({ action: 'processQuestion', query: text }, resp => {
      const answer = resp.answer || "Sorry, something went wrong.";
      addBubble('bot', answer);
    });
  }

  function addBubble(sender, text) {
    const div = document.createElement('div');
    div.className = `message ${sender}`;
    const p = document.createElement('p');
    p.textContent = text;
    div.appendChild(p);
    chatContainer.appendChild(div);
    chatContainer.scrollTop = chatContainer.scrollHeight;
  }
});
