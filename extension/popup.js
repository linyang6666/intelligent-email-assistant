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

  // Pagination params
  let offset = 0;
  const limit = 10;

  /**
  * Load and render a page of emails, with manual labeling support.
  * @param {boolean} append - If true, appends to existing list; otherwise resets list.
  */
  function loadEmails(append = false) {
    // Reset offset and clear list if not appending
    if (!append) {
      offset = 0;
      emailListEl.innerHTML = '<strong>Recent Emails:</strong>';
    }

    // Fetch a page of emails from backend
    fetch(`http://127.0.0.1:5000/api/emails?offset=${offset}&limit=${limit}`)
      .then(res => res.json())
      .then(emails => {
        // Iterate over each email and render
        emails.forEach(e => {
          // Container for a single email item
          const div = document.createElement('div');
          div.className = 'email-item';
          div.dataset.id = e.id;

          // Build HTML for subject, sender, and snippet
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
            <div class="snippet">${e.snippet}...</div>
        ` ;

          // Create "edit" arrow button to toggle the dropdown
          const editBtn = document.createElement('button');
          editBtn.className = 'edit-btn';
          editBtn.textContent = '✎';    // or use '✎'

          // Create the dropdown for manual labeling (initially hidden)
          const select = document.createElement('select');
          select.className = 'tag-selector';
          select.style.display = 'none';  // hide by default

          // Populate dropdown options
          ['default', 'spam', 'urgent', 'business', 'friendly', 'complaint']
            .forEach(tag => {
              const opt = document.createElement('option');
              opt.value = tag;
              opt.textContent = tag.charAt(0).toUpperCase() + tag.slice(1);
              if (tag === e.tag) opt.selected = true;
              select.appendChild(opt);
            });

          // Create status indicator for save feedback
          const status = document.createElement('span');
          status.className = 'save-status';

          // Toggle dropdown on click
          editBtn.addEventListener('click', () => {
            select.style.display = select.style.display === 'none' ? 'block' : 'none';
          });

          // Handle manual label changes
          select.addEventListener('change', () => {
            fetch('http://127.0.0.1:5000/api/label', {
              method: 'POST',
              headers: {'Content-Type': 'application/json'},
              body: JSON.stringify({ id: e.id, manual_tag: select.value })
            })
            .then(r => r.json())
            .then(resp => {
              // Show checkmark on success, cross on failure
              status.textContent = resp.status === 'ok' ? '✓' : '✗';
            })
            .catch(() => {
              status.textContent = '✗';
            });
          });

          // Append arrow, dropdown, and status to the email item
          div.appendChild(editBtn);
          div.appendChild(select);
          div.appendChild(status);

          // Append the item to the list
          emailListEl.appendChild(div);
        });

        // Advance offset for next page
        offset += limit;
      })
      .catch(() => {
        // Show error if fetch fails
        emailListEl.innerHTML += '<div class="email-item">Failed to load emails.</div>';
      });
  }

  // "More" button
  document.getElementById('load-more').addEventListener('click', () => {
    loadEmails(true);
  });

  // "View Eval Report" button
  document.getElementById('view-eval').addEventListener('click', () => {
    fetch('http://127.0.0.1:5000/api/eval')
      .then(r => r.json())
      .then(report => {
        document.getElementById('eval-report').textContent = JSON.stringify(report, null, 2);
      })
      .catch(() => {
        document.getElementById('eval-report').textContent = 'Failed to fetch report.';
      });
  });

  // Initial load of emails
  loadEmails(false);

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

  // 4. Chat send & clear logic
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
  // Existing To-Do functions
  // -----------------------
  function renderTodos(items) {
    todoItemsEl.innerHTML = '';
    if (!items || items.length === 0) {
      const li = document.createElement('li');
      li.className = 'todo-item loading';
      li.textContent = 'No to-dos found.';
      todoItemsEl.appendChild(li);
      return;
    }
    items.forEach(text => {
      const li = document.createElement('li');
      li.className = 'todo-item';
      const checkbox = document.createElement('input');
      checkbox.type = 'checkbox';
      checkbox.addEventListener('change', () => {
        li.style.textDecoration = checkbox.checked ? 'line-through' : 'none';
      });
      const span = document.createElement('span');
      span.textContent = text.replace(/^\d+\.\s*/, '');
      li.appendChild(checkbox);
      li.appendChild(span);
      todoItemsEl.appendChild(li);
    });
  }

  function fetchTodos(force = false) {
    todoItemsEl.innerHTML = '<li class="todo-item loading">Refreshing to-dos...</li>';
    const url = 'http://127.0.0.1:5000/api/todos' + (force ? '?refresh=true' : '');
    fetch(url)
      .then(res => res.json())
      .then(data => {
        const items = Array.isArray(data.todos) ? data.todos : [];
        renderTodos(items);
      })
      .catch(error => {
        console.error('Error fetching to-dos:', error);
        renderTodos([]);
      });
  }

  toggleBtn.addEventListener('click', () => {
    todoListEl.classList.toggle('collapsed');
  });

  refreshBtn.addEventListener('click', () => {
    fetchTodos(true);
  });

  // -----------------------
  // Existing Chat functions
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