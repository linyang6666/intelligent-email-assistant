# Gmail Assistant

A Chrome extension integrated with a Flask backend to intelligently manage and query your Gmail. Fetch recent emails, filter spam, and generate email summaries instantly through natural-language queries.

## Quickstart

**Backend Setup:**

Ensure Python 3.8+ is installed.

## Setup & Run

1. **Backend**  
   ```bash
   - cd server
   - pip install -r requirements.txt
   - python background.py

2. **Chrome Extension**  
   - Open Chrome’s Extensions page (`chrome://extensions/`), enable Developer mode and click **Load unpacked**, selecting the `extension/` folder.  
   - You will see a “Gmail Assistant” icon appear in your toolbar.

## Usage

- Click the “Gmail Assistant” icon to open the popup.  
- The top panel lists your 10 most recent emails (sender, subject, snippet).  
- Type any question—e.g.  
  - “Show me emails from Alice.”  
  - “Filter spam from the last 100 messages and summarize.”  
  - “What did Bob say yesterday?”  
- Press Enter or click **Send**. The extension will forward your query to the backend, which builds context from cached emails and returns an answer powered by OpenAI.

## Features

- **Email Fetching**: Automatically pulls up to 100 recent messages every 5 min.  
- **Keyword Search**: Finds relevant emails by keyword; falls back to the latest 10 if no matches.  
- **Spam Filter & Summary**: Detects queries about “spam” and asks the model to identify and summarize spam from the latest 100 emails.  
- **Chat Interface**: Displays conversation history and a “Thinking…” indicator during LLM calls.