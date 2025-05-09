# server/ai_processor.py

from openai import OpenAI
from dotenv import load_dotenv
import os

# Load environment variables from openAI_Key.env
load_dotenv('openAI_Key.env')

class AIProcessor:
    def __init__(self, api_key=None):
        """
        Initialize the OpenAI API client using an environment variable or provided key.
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API key not found in environment")
        self.client = OpenAI(api_key=self.api_key)

    def prepare_context(self, emails, query):
        """
        Format the most recent emails and user query into a prompt for OpenAI.
        """
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
            context += f"Snippet: {email['body'][:300]}...\n\n"

        context += (
            f"User question: {query}\n\n"
            "Please answer the user's question in a helpful tone.\n"
            "Then, add a summary of what the emails are about and suggest one helpful action the user might take.\n"
            "Format your reply like this:\n"
            "Summary: ...\n"
            "Suggested Action: ..."
        )

        return context

    def query_openai(self, context, query):
        """
        Query OpenAI with the formatted email context and user question.
        Returns the generated response from the language model.
        """
        try:
            resp = self.client.chat.completions.create(
                model="gpt-4o-mini-2024-07-18",  # Use appropriate model
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that answers questions about emails."},
                    {"role": "user", "content": context}
                ],
                max_tokens=400,
                temperature=0.7
            )
            return resp.choices[0].message.content.strip()
        except Exception as e:
            return f"Error processing question: {e}"

    def search_emails(self, emails, query):
        """
        Perform keyword-based search on emails to find relevant messages.
        """
        relevant_emails = []
        keywords = query.lower().split()

        for email in emails:
            email_text = f"{email['subject']} {email['body']}".lower()
            if any(keyword in email_text for keyword in keywords):
                relevant_emails.append(email)

        return relevant_emails

    def build_filter_summary_context(self, emails, instruction: str) -> str:
        """
        Build a prompt context for spam filtering and summarization based on email content.
        """
        ctx = instruction + "\n\n"
        for i, e in enumerate(emails, 1):
            snippet = e['body'][:100].replace('\n', ' ')
            
            # Add tag if available
            tag_info = ""
            if "tag" in e:
                emoji = self.get_emoji_for_tag(e["tag"])
                tag_info = f" [{emoji} {e['tag'].capitalize()}]"
                
            ctx += (
                f"Email {i}:\n"
                f"  From: {e['sender']}\n"
                f"  Subject: {e['subject']}\n"
                f"  Snippet: {snippet}...\n\n"
            )
        ctx += "\nPlease give a direct spam list and a comprehensive summary."
        return ctx
        
    def get_emoji_for_tag(self, tag):
        """Convert tag to emoji representation"""
        emoji_map = {
            "urgent": "⚠️",
            "business": "💼",
            "friendly": "😊",
            "complaint": "😡",
            "default": " "
        }
        return emoji_map.get(tag, "")

