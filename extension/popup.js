// popup.js - Chrome Extension UI

document.addEventListener("DOMContentLoaded", function() {
    const emailListEl   = document.getElementById("email-list");
    const chatContainer = document.getElementById("chat-container");
    const userInput     = document.getElementById("user-input");
    const sendButton    = document.getElementById("send-button");

    // 1. Pull recent emails at initialization
    fetch('http://localhost:5000/api/emails')
      .then(res => res.json())
      .then(emails => {
        emailListEl.innerHTML = '<strong>Recent Emails:</strong>';
        emails.forEach(e => {
          const div = document.createElement("div");
          div.classList.add("email-item");
          div.innerHTML = `
            <div class="subject">${e.subject}</div>
            <div class="from">From: ${e.sender}</div>
            <div class="snippet">${e.snippet}…</div>
          `;
          emailListEl.appendChild(div);
        });
      })
      .catch(err => {
        emailListEl.textContent = "Failed to load emails.";
        console.error(err);
      });

    // 2. Initializing Chat Conversations
    addMessage("bot", "Hello! I can help answer questions about your emails. What would you like to know?");

    // 3. Send Button & Enter Event
    sendButton.addEventListener("click", sendMessage);
    userInput.addEventListener("keypress", function(e) {
        if (e.key === "Enter") {
            sendMessage();
        }
    });

    function sendMessage() {
        const message = userInput.value.trim();
        if (!message) return;

        addMessage("user", message);
        userInput.value = "";

        addMessage("bot", "Thinking...", "thinking");

        chrome.runtime.sendMessage(
            { action: "processQuestion", query: message },
            function(response) {
                // Remove thinking tip
                const thinkingEl = document.querySelector(".thinking");
                if (thinkingEl) thinkingEl.remove();

                addMessage("bot", response.answer);
            }
        );
    }

    function addMessage(sender, text, className = "") {
        const messageDiv = document.createElement("div");
        messageDiv.classList.add("message", sender);
        if (className) messageDiv.classList.add(className);

        const contentP = document.createElement("p");
        contentP.textContent = text;
        messageDiv.appendChild(contentP);

        chatContainer.appendChild(messageDiv);
        chatContainer.scrollTop = chatContainer.scrollHeight;
    }
});
