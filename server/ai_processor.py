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
            context += f"Email {i + 1}:\n"
            context += f"From: {email['sender']}\n"
            context += f"Subject: {email['subject']}\n"
            context += f"Snippet: {email['body'][:150]}...\n\n"

        context += f"\nUser question: {query}\n"
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
                max_tokens=500,
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
            ctx += (
                f"Email {i}:\n"
                f"  From: {e['sender']}\n"
                f"  Subject: {e['subject']}\n"
                f"  Snippet: {snippet}...\n\n"
            )
        ctx += "\nPlease give a direct spam list and a comprehensive summary."
        return ctx
