// popup.js

document.addEventListener('DOMContentLoaded', () => {
  const emailListEl    = document.getElementById('email-list');
  const todoItemsEl    = document.getElementById('todo-items');
  const chatContainer  = document.getElementById('chat-container');
  const userInput      = document.getElementById('user-input');
  const sendButton     = document.getElementById('send-button');
  const clearButton    = document.getElementById('clear-history');
  const WELCOME        = 'Hello! I can help answer questions about your emails. What would you like to know?';


  // Fetch & render emails (unchanged) …
  fetch('http://127.0.0.1:5000/api/emails')
    .then(res => res.json())
    .then(emails => {
      emailListEl.innerHTML = '<strong>Recent Emails:</strong>';
      emails.forEach(e => {
        const div = document.createElement('div');
        div.className = 'email-item';

        let tagHTML = '';
        if (e.tag && e.tag !== 'default') {
          const emoji = e.tagEmoji || '';
          tagHTML = `<span class="tag tag-${e.tag}">${emoji} ${capitalize(e.tag)}</span>`;
        }

        let spamTag = '';
        if (e.is_spam) {
          spamTag = `<span class="tag tag-spam">🚫 Spam</span>`;
        }

        div.innerHTML = `
          <div class="subject">
            <span>${e.subject}</span>
            ${tagHTML}
          </div>
          <div class="from">From: ${e.sender}</div>
          <div class="snippet">${e.snippet}…</div>`;
        emailListEl.appendChild(div);
      });
    })
    .catch(_ => emailListEl.textContent = 'Failed to load emails.');

  // Fetch and render the To-Do list from backend
fetch('http://127.0.0.1:5000/api/todos')
  .then(response => response.json())
  .then(data => {
    const container = document.getElementById('todo-items');
    // Clear any existing content (e.g., loading placeholder)
    container.innerHTML = '';

    if (Array.isArray(data.todos) && data.todos.length > 0) {
      data.todos.forEach(item => {
        const li = document.createElement('li');
        li.className = 'todo-item';

        // Create a checkbox to mark the item as completed
        const checkbox = document.createElement('input');
        checkbox.type = 'checkbox';
        checkbox.addEventListener('change', () => {
          // Toggle strikethrough styling; persistence to storage can be added here
          li.style.textDecoration = checkbox.checked ? 'line-through' : 'none';
        });

        // Create a span for the to-do text
        const textSpan = document.createElement('span');
        // Strip any leading numbering (e.g., "1. ") from the item
        textSpan.textContent = item.replace(/^\d+\.\s*/, '');

        li.appendChild(checkbox);
        li.appendChild(textSpan);
        container.appendChild(li);
      });
    } else {
      // Display message when no to-dos are available
      const li = document.createElement('li');
      li.className = 'todo-item loading';
      li.textContent = 'No to-dos found.';
      container.appendChild(li);
    }
  })
  .catch(error => {
    const container = document.getElementById('todo-items');
    // Clear any partial content and show error message
    container.innerHTML = '';
    const li = document.createElement('li');
    li.className = 'todo-item loading';
    li.textContent = 'Failed to load to-dos.';
    container.appendChild(li);
    console.error('Error fetching to-dos:', error);
  });


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

  function capitalize(word) {
    return word.charAt(0).toUpperCase() + word.slice(1);
  }
});
