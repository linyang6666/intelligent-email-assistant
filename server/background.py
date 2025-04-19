# server/background.py

import threading
import time
import os

from flask import Flask, request, jsonify
from flask_cors import CORS

# 相对导入重命名后的模块
from gmail_connector import GmailConnector
from ai_processor import AIProcessor

app = Flask(__name__)
CORS(app)

# 全局状态
gmail_connector = None
ai_processor = None
email_cache = []
last_fetch_time = 0


def initialize_services():
    """初始化 Gmail 和 OpenAI 服务"""
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
    """每 5 分钟拉取一次最新邮件"""
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
    return jsonify({'status': 'ok'})


@app.route('/api/query', methods=['POST'])
def process_query():
    data  = request.json or {}
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
        context = ai_processor.prepare_context(relevant, query)
        answer  = ai_processor.query_openai(context, query)

    return jsonify({'answer': answer})

@app.route('/api/emails', methods=['GET'])
def get_emails():
    """返回最近拉取到的前 10 封邮件"""
    refresh_email_cache()
    # 返回简化字段：id, sender, subject, snippet
    simplified = []
    for e in email_cache[:10]:
        simplified.append({
            "id": e["id"],
            "sender": e["sender"],
            "subject": e["subject"],
            "snippet": e["body"][:100]  # 摘要
        })
    return jsonify(simplified)


if __name__ == "__main__":
    threading.Thread(target=initialize_services).start()
    app.run(debug=True, port=5000)
