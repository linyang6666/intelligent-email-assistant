// popup.js

document.addEventListener('DOMContentLoaded', () => {
  const emailListEl   = document.getElementById('email-list');
  const chatContainer = document.getElementById('chat-container');
  const userInput     = document.getElementById('user-input');
  const sendButton    = document.getElementById('send-button');
  const clearButton   = document.getElementById('clear-history');
  const WELCOME       = 'Hello! I can help answer questions about your emails. What would you like to know?';

  // To-Do related elements
  const todoItemsEl = document.getElementById('todo-items');
  const todoListEl  = document.getElementById('todo-list');
  const toggleBtn   = document.getElementById('todo-toggle');
  const refreshBtn  = document.getElementById('todo-refresh');

  /**
   * Render an array of to-do items into the UI.
   * @param {string[]} items - List of to-do strings.
   */
  function renderTodos(items) {
    // Clear current list
    todoItemsEl.innerHTML = '';

    if (!items || items.length === 0) {
      // Display placeholder when there are no items
      const li = document.createElement('li');
      li.className = 'todo-item loading';
      li.textContent = 'No to-dos found.';
      todoItemsEl.appendChild(li);
      return;
    }

    // Populate each to-do entry with a checkbox and text
    items.forEach(text => {
      const li = document.createElement('li');
      li.className = 'todo-item';

      const checkbox = document.createElement('input');
      checkbox.type = 'checkbox';
      // Toggle strikethrough on check/uncheck
      checkbox.addEventListener('change', () => {
        li.style.textDecoration = checkbox.checked ? 'line-through' : 'none';
      });

      const span = document.createElement('span');
      // Remove any leading numbering (e.g., "1. ")
      span.textContent = text.replace(/^\d+\.\s*/, '');

      li.appendChild(checkbox);
      li.appendChild(span);
      todoItemsEl.appendChild(li);
    });
  }

  /**
   * Fetch To-Do list from backend and render it.
   * @param {boolean} force - If true, bypass server cache via ?refresh=true.
   */
  function fetchTodos(force = false) {
    // Show loading indicator
    todoItemsEl.innerHTML = '<li class="todo-item loading">Refreshing to-dos…</li>';

    const url = 'http://127.0.0.1:5000/api/todos' + (force ? '?refresh=true' : '');
    fetch(url)
      .then(res => res.json())
      .then(data => {
        const items = Array.isArray(data.todos) ? data.todos : [];
        renderTodos(items);
      })
      .catch(error => {
        console.error('Error fetching to-dos:', error);
        renderTodos([]);  // fallback to empty state
      });
  }

  // -----------------------
  // Event Listeners
  // -----------------------

  // Collapse/expand To-Do panel
  toggleBtn.addEventListener('click', () => {
    todoListEl.classList.toggle('collapsed');
  });

  // Manual refresh button
  refreshBtn.addEventListener('click', () => {
    fetchTodos(true);
  });

  // -----------------------
  // Initial Data Loading
  // -----------------------

  // 1. Load recent emails (unchanged logic)
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

  // 2. Load To-Do list without forcing cache
  fetchTodos(false);

  // 3. Load & render chat history
  chrome.runtime.sendMessage({ action: 'getHistory' }, resp => {
    const history = resp.history || [];
    chatContainer.innerHTML = '';
    if (history.length === 0) {
      addBubble('bot', WELCOME);
    } else {
      history.forEach(m => addBubble(m.sender, m.text));
    }
  });

  // 4. Chat send & clear logic (unchanged)
  sendButton.addEventListener('click', onSend);
  userInput.addEventListener('keypress', e => {
    if (e.key === 'Enter') onSend();
  });
  clearButton.addEventListener('click', () => {
    chrome.storage.local.set({ messages: [] }, () => {
      chatContainer.innerHTML = '';
      addBubble('bot', WELCOME);
    });
  });

  // -----------------------
  // Helper Functions
  // -----------------------

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
