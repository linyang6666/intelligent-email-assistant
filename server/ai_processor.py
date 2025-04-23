# server/ai_processor.py

from openai import OpenAI
from dotenv import load_dotenv
import os

load_dotenv('openAI_Key.env')

class AIProcessor:
    def __init__(self, api_key=None):
        # 初始化 OpenAI 客户端
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API key not found in environment")
        self.client = OpenAI(api_key=self.api_key)

    def prepare_context(self, emails, query):
        """Prepare email context for the OpenAI query"""
        context = "Here are the most recent emails:\n\n"

        for i, email in enumerate(emails[:10]):  # Use top 10 for immediate context
            # Add tag if available
            tag_info = ""
            if "tag" in email:
                emoji = self.get_emoji_for_tag(email["tag"])
                tag_info = f" [{emoji} {email['tag'].capitalize()}]"
                
            context += f"Email {i + 1}:{tag_info}\n"
            context += f"From: {email['sender']}\n"
            context += f"Subject: {email['subject']}\n"
            context += f"Snippet: {email['body'][:150]}...\n\n"

        context += f"\nUser question: {query}\n"
        return context

    def query_openai(self, context, query):
        """Send the context and query to OpenAI and get a response"""
        try:
            resp = self.client.chat.completions.create(
                model="gpt-4o-mini-2024-07-18",  # Use appropriate model
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that answers questions about emails."},
                    {"role": "user", "content": context}
                ],
                max_tokens=500,
                temperature=0.7
            )
            # 提取并返回生成的文本
            return resp.choices[0].message.content.strip()
        except Exception as e:
            return f"Error processing question: {e}"

    def search_emails(self, emails, query):
        """Search emails for relevant information to the query"""
        relevant_emails = []
        keywords = query.lower().split()

        for email in emails:
            email_text = f"{email['subject']} {email['body']}".lower()
            if any(keyword in email_text for keyword in keywords):
                relevant_emails.append(email)

        return relevant_emails

    def build_filter_summary_context(self, emails, instruction: str) -> str:
        """
        构造一个 prompt，让 LLM 对给定的 emails 列表根据 instruction
        进行垃圾邮件过滤和摘要。
        """
        ctx = instruction + "\n\n"
        for i, e in enumerate(emails, 1):
            # 这里只取 id, subject, snippet
            snippet = e['body'][:100].replace('\n', ' ')
            
            # Add tag if available
            tag_info = ""
            if "tag" in e:
                emoji = self.get_emoji_for_tag(e["tag"])
                tag_info = f" [{emoji} {e['tag'].capitalize()}]"
                
            ctx += (
                f"邮件 {i}:{tag_info}\n"
                f"  发件人: {e['sender']}\n"
                f"  主题: {e['subject']}\n"
                f"  摘要: {snippet}...\n\n"
            )
        ctx += "\n请直接给出垃圾邮件列表和综合摘要。"
        return ctx
        
    def get_emoji_for_tag(self, tag):
        """Convert tag to emoji representation"""
        emoji_map = {
            "urgent": "⚠️",
            "business": "💼",
            "friendly": "😊",
            "complaint": "😡"
        }
        return emoji_map.get(tag, "")