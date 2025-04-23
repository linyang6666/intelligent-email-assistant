# server/background.py

import threading
import time
import os

from flask import Flask, request, jsonify
from flask_cors import CORS

# 相对导入重命名后的模块
from gmail_connector import GmailConnector
from ai_processor import AIProcessor
from email_classifier import EmailClassifier  # Import the new module

app = Flask(__name__)
CORS(app)

# 全局状态
gmail_connector = None
ai_processor = None
email_classifier = None  # New classifier
email_cache = []
last_fetch_time = 0
classified_emails = []  # Cache for classified emails


def initialize_services():
    """初始化 Gmail 和 OpenAI 服务"""
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
    """每 5 分钟拉取一次最新邮件"""
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


def classify_emails_background():
    """Background task to classify emails"""
    global email_cache, classified_emails
    try:
        # Only classify the first 20 emails to save API costs
        classified_emails = email_classifier.classify_emails(email_cache, max_emails=20)
        print(f"Classified {len(classified_emails)} emails")
    except Exception as e:
        print(f"Error classifying emails: {e}")


@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'ok'})


@app.route('/api/query', methods=['POST'])
def process_query():
    data = request.json or {}
    query = data.get('query', '').strip()
    if not query:
        return jsonify({'error': 'No query provided'}), 400

    # 刷新邮件缓存
    refresh_email_cache()

    # 如果用户想筛选垃圾邮件并摘要
    q_lower = query.lower()
    if '垃圾邮件' in query or 'spam' in q_lower:
        # 从最近 100 封中筛选垃圾邮件并摘要
        target = email_cache[:100]
        context = ai_processor.build_filter_summary_context(
            target,
            instruction="请帮我从这 100 封邮件中筛选出垃圾邮件，并给出一个摘要。"
        )
        answer = ai_processor.query_openai(context, query)
    else:
        # 普通检索：先关键词匹配
        relevant = ai_processor.search_emails(email_cache, query)
        # 如果没匹配到，兜底使用最近 10 封
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
    """返回最近拉取到的前 10 封邮件"""
    refresh_email_cache()
    
    # 尝试使用已分类的邮件
    emails_to_return = []
    
    # Get IDs of the first 10 emails
    top_email_ids = [e["id"] for e in email_cache[:10]]
    
    # For each ID, check if we have a classified version
    for email_id in top_email_ids:
        # Find classified version
        classified_version = next(
            (e for e in classified_emails if e["id"] == email_id), 
            None
        )
        
        # Find original version
        original_version = next(
            (e for e in email_cache if e["id"] == email_id),
            None
        )
        
        if classified_version:
            emails_to_return.append(classified_version)
        elif original_version:
            emails_to_return.append(original_version)
    
    # 返回简化字段：id, sender, subject, snippet, tag
    simplified = []
    for e in emails_to_return:
        email_data = {
            "id": e["id"],
            "sender": e["sender"],
            "subject": e["subject"],
            "snippet": e["body"][:100]  # 摘要
        }
        
        # Add tag and emoji if available
        if "tag" in e:
            email_data["tag"] = e["tag"]
            email_data["tagEmoji"] = email_classifier.get_emoji_for_tag(e["tag"])
            
        simplified.append(email_data)
        
    return jsonify(simplified)


if __name__ == "__main__":
    threading.Thread(target=initialize_services).start()
    app.run(debug=True, port=5000)