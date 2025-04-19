# background.py - Background Service
import flask
from flask import Flask, request, jsonify
from flask_cors import CORS
import threading
import json
import os

from gmail_connector import GmailConnector
from ai_processor import AIProcessor

app = Flask(__name__)
CORS(app)

# Global variables
gmail_connector = None
ai_processor = None
email_cache = []
last_fetch_time = 0

def initialize_services():
    """Initialize the Gmail and OpenAI services"""
    global gmail_connector, ai_processor
    
    # Initialize Gmail connector
    gmail_connector = GmailConnector()
    try:
        gmail_connector.authenticate()
        print("Gmail authentication successful")
    except Exception as e:
        print(f"Gmail authentication failed: {str(e)}")
    
    # Initialize OpenAI processor
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("Warning: OpenAI API key not found in environment variables")
    ai_processor = AIProcessor(api_key)
    
    # Initial fetch of emails
    refresh_email_cache()

def refresh_email_cache():
    """Refresh the email cache with the latest emails"""
    global email_cache, last_fetch_time
    import time
    
    current_time = time.time()
    # Only refresh if it's been more than 5 minutes
    if current_time - last_fetch_time < 300:
        return
        
    try:
        email_cache = gmail_connector.get_recent_emails(max_emails=100)
        last_fetch_time = current_time
        print(f"Email cache refreshed with {len(email_cache)} emails")
    except Exception as e:
        print(f"Error refreshing email cache: {str(e)}")

@app.route('/api/query', methods=['POST'])
def process_query():
    """Process a user query about emails"""
    data = request.json
    query = data.get('query', '')
    
    if not query:
        return jsonify({'error': 'No query provided'}), 400
    
    # Refresh email cache if needed
    refresh_email_cache()
    
    # Search for relevant emails
    relevant_emails = ai_processor.search_emails(email_cache, query)
    
    # Prepare context and query OpenAI
    context = ai_processor.prepare_context(relevant_emails, query)
    response = ai_processor.query_openai(context, query)
    
    return jsonify({'answer': response})

@app.route('/api/health', methods=['GET'])
def health_check():
    """Simple health check endpoint"""
    return jsonify({'status': 'ok'})

# Chrome extension manifest.json
manifest = {
    "manifest_version": 3,
    "name": "Gmail Assistant",
    "version": "1.0",
    "description": "AI-powered assistant for Gmail",
    "permissions": ["activeTab", "storage", "identity", "https://mail.google.com/*"],
    "host_permissions": ["https://mail.google.com/*"],
    "background": {
        "service_worker": "background.js"
    },
    "action": {
        "default_popup": "popup.html",
        "default_icon": {
            "16": "icons/icon16.png",
            "48": "icons/icon48.png",
            "128": "icons/icon128.png"
        }
    },
    "oauth2": {
        "client_id": "YOUR_CLIENT_ID.apps.googleusercontent.com",
        "scopes": ["https://www.googleapis.com/auth/gmail.readonly"]
    }
}

# Chrome extension background.js
background_js = """
// Background script for Chrome extension
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
"""

if __name__ == "__main__":
    # Initialize services in a separate thread
    threading.Thread(target=initialize_services).start()
    
    # Start Flask server
    app.run(debug=True, port=5000)