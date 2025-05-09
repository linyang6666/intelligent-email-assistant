# server/background.py

import threading
import time
import os

from flask import Flask, request, jsonify
from flask_cors import CORS

# Import Gmail and AI processing modules
from gmail_connector import GmailConnector
from ai_processor import AIProcessor
from email_classifier import EmailClassifier  # Import the new module

app = Flask(__name__)
CORS(app)

# Global service instances and email cache
gmail_connector = None
ai_processor = None
email_classifier = None  # New classifier
email_cache = []
last_fetch_time = 0
classified_emails = []  # Cache for classified emails

todo_cache = []
last_todo_time = 0


def initialize_services():
    """
    Initialize GmailConnector and AIProcessor instances.
    Authenticate Gmail access and fetch initial email cache.
    """
    global gmail_connector, ai_processor, email_classifier


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
    email_classifier = EmailClassifier(api_key)  # Initialize the classifier

    refresh_email_cache()


def refresh_email_cache():
    """
    Refresh email cache if more than 5 minutes have passed since last fetch.
    """
    global email_cache, last_fetch_time, classified_emails

    now = time.time()
    if now - last_fetch_time < 300:
        return

    try:
        email_cache = gmail_connector.get_recent_emails(max_emails=100)
        last_fetch_time = now
        print(f"Email cache refreshed: {len(email_cache)} emails")
        
        # Classify emails in a non-blocking way
        threading.Thread(target=classify_emails_background).start()
        
    except Exception as e:
        print(f"Error refreshing email cache: {e}")

def refresh_todo_cache():
    """
    Generate and cache To-Do items based on latest emails.
    Refreshes only if cache is older than 5 minutes.
    """
    global todo_cache, last_todo_time

    now = time.time()
    # Reuse cache if it was updated within the last 5 minutes
    if now - last_todo_time < 300 and todo_cache:
        return

    # Ensure email cache is up‐to‐date
    refresh_email_cache()

    # Prepare email list for To-Do generation
    emails = []
    for e in email_cache[:10]:
        classified = next((c for c in classified_emails if c["id"] == e["id"]), None)
        emails.append(classified or e)

    # Call AIProcessor to generate raw To-Do text
    raw_output = ai_processor.generate_todo_list(emails, max_items=5)
    # Split lines and filter out empty entries
    todos = [line.strip() for line in raw_output.splitlines() if line.strip()]

    # Update cache
    todo_cache = todos
    last_todo_time = now

def classify_emails_background():
    """Background task to classify emails"""
    global email_cache, classified_emails
    try:
        # Only classify the first 20 emails to save API costs
        classified_emails = email_classifier.classify_emails(email_cache, max_emails=20)

        # Add spam detection field
        for email in classified_emails:
            email["is_spam"] = email_classifier.is_spam(email)

        print(f"Classified {len(classified_emails)} emails")
    except Exception as e:
        print(f"Error classifying emails: {e}")


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
    # q_lower = query.lower()
    # if 'junk mail' in query or 'spam' in q_lower:
    #     target = email_cache[:100]
    #     context = ai_processor.build_filter_summary_context(
    #         target,
    #         instruction="Please filter spam from the following 100 emails and generate a summary."
    #     )
    #     answer = ai_processor.query_openai(context, query)
    q_lower = query.lower()
    if 'spam' in q_lower or 'junk mail' in q_lower:
        spam_emails = [e for e in classified_emails if e.get("is_spam")]
        if not spam_emails:
            return jsonify({'answer': "No spam emails found."})
        
        summary = "Here are the spam emails detected:\n\n"
        for e in spam_emails[:5]:
            summary += f"- From: {e['sender']}, Subject: {e['subject']}\n"
        
        return jsonify({'answer': summary})

    else:
        # General keyword-based email search
        relevant = ai_processor.search_emails(email_cache, query)
        if not relevant:

            relevant = email_cache[:10]
            
        # Try to use classified emails if available
        emails_to_use = []
        for email in relevant:
            # Look for the classified version of this email
            classified_version = next(
                (e for e in classified_emails if e["id"] == email["id"]), 
                None
            )
            if classified_version:
                emails_to_use.append(classified_version)
            else:
                emails_to_use.append(email)
                
        context = ai_processor.prepare_context(emails_to_use, query)

        answer = ai_processor.query_openai(context, query)

    return jsonify({'answer': answer})


@app.route('/api/emails', methods=['GET'])
def get_emails():
    refresh_email_cache()

    top_ids = [e["id"] for e in email_cache[:10]]
    emails_to_return = []

    for email_id in top_ids:
        classified = next((e for e in classified_emails if e["id"] == email_id), None)
        original = next((e for e in email_cache if e["id"] == email_id), None)
        chosen = classified or original
        if chosen:
            tag = chosen.get("tag", "default")
            emails_to_return.append({
                "id": chosen["id"],
                "sender": chosen["sender"],
                "subject": chosen["subject"],
                "snippet": chosen["body"][:100],
                "tag": tag,
                "tagEmoji": email_classifier.get_emoji_for_tag(tag),
                "is_spam": chosen.get("is_spam", False)
            })

    return jsonify(emails_to_return)

@app.route('/api/todos', methods=['GET'])
def get_todo_list():
    """
    Return cached To-Do items, regenerating if cache expired or if force-refresh is requested.
    """
    # Check for manual refresh flag in query string
    force_refresh = request.args.get('refresh', 'false').lower() == 'true'
    if force_refresh:
        # Invalidate cache timestamp so refresh_todo_cache() will regenerate
        global last_todo_time
        last_todo_time = 0

    try:
        refresh_todo_cache()
        return jsonify({'todos': todo_cache})
    except Exception as e:
        return jsonify({'error': f'Failed to retrieve todos: {e}'}), 500




if __name__ == "__main__":
    # Start background thread to initialize services before serving requests
    threading.Thread(target=initialize_services).start()
    app.run(debug=True, port=5000)
