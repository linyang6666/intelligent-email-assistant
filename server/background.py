# server/background.py

import threading
import time
import os

from flask import Flask, request, jsonify
from flask_cors import CORS

# Import Gmail and AI processing modules
from gmail_connector import GmailConnector
from ai_processor import AIProcessor

app = Flask(__name__)
CORS(app)

# Global service instances and email cache
gmail_connector = None
ai_processor = None
email_cache = []
last_fetch_time = 0


def initialize_services():
    """
    Initialize GmailConnector and AIProcessor instances.
    Authenticate Gmail access and fetch initial email cache.
    """
    global gmail_connector, ai_processor

    gmail_connector = GmailConnector()
    try:
        gmail_connector.authenticate()
        print("Gmail authentication successful")
    except Exception as e:
        print(f"Gmail authentication failed: {e}")

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("Warning: OPENAI_API_KEY not set")
    ai_processor = AIProcessor(api_key)

    refresh_email_cache()


def refresh_email_cache():
    """
    Refresh email cache if more than 5 minutes have passed since last fetch.
    """
    global email_cache, last_fetch_time
    now = time.time()
    if now - last_fetch_time < 300:
        return

    try:
        email_cache = gmail_connector.get_recent_emails(max_emails=100)
        last_fetch_time = now
        print(f"Email cache refreshed: {len(email_cache)} emails")
    except Exception as e:
        print(f"Error refreshing email cache: {e}")


@app.route('/api/health', methods=['GET'])
def health_check():
    """Simple health check endpoint."""
    return jsonify({'status': 'ok'})


@app.route('/api/query', methods=['POST'])
def process_query():
    """
    Process user query:
    - If spam-related, instruct LLM to filter and summarize.
    - Otherwise, search relevant emails or fall back to latest 10.
    """
    data = request.json or {}
    query = data.get('query', '').strip()
    if not query:
        return jsonify({'error': 'No query provided'}), 400

    # Ensure email cache is up-to-date
    refresh_email_cache()

    # Spam filtering path
    q_lower = query.lower()
    if '垃圾邮件' in query or 'spam' in q_lower:
        target = email_cache[:100]
        context = ai_processor.build_filter_summary_context(
            target,
            instruction="Please filter spam from the following 100 emails and generate a summary."
        )
        answer = ai_processor.query_openai(context, query)
    else:
        # General keyword-based email search
        relevant = ai_processor.search_emails(email_cache, query)
        if not relevant:
            relevant = email_cache[:10]  # fallback
        context = ai_processor.prepare_context(relevant, query)
        answer = ai_processor.query_openai(context, query)

    return jsonify({'answer': answer})


@app.route('/api/emails', methods=['GET'])
def get_emails():
    """
    Return the latest 10 emails with simplified fields:
    id, sender, subject, and snippet (first 100 characters of body).
    """
    refresh_email_cache()
    simplified = []
    for e in email_cache[:10]:
        simplified.append({
            "id": e["id"],
            "sender": e["sender"],
            "subject": e["subject"],
            "snippet": e["body"][:100]
        })
    return jsonify(simplified)


if __name__ == "__main__":
    # Start background thread to initialize services before serving requests
    threading.Thread(target=initialize_services).start()
    app.run(debug=True, port=5000)
