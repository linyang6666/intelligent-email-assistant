# server/email_classifier.py

from openai import OpenAI
import os

class EmailClassifier:
    def __init__(self, api_key=None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API key not found in environment")
        self.client = OpenAI(api_key=self.api_key)
        
    def classify_emails(self, emails, max_emails=20):
        """
        Classify a batch of emails by intent and sentiment
        Returns emails with added 'tag' field containing one of:
        'urgent', 'business', 'friendly', 'complaint', 'default', 'spam'
        """
        # Only process up to max_emails
        emails_to_process = emails[:max_emails]
        
        # Prepare batch context
        email_texts = []
        for i, email in enumerate(emails_to_process):
            # Use subject and snippet
            email_text = f"Email {i+1}:\nFrom: {email['sender']}\nSubject: {email['subject']}\n"
            email_text += f"Snippet: {email['body'][:150]}...\n\n"
            email_texts.append(email_text)
        
        context = "Classify each email into exactly one of these categories:\n"
        context += "1. spam - Unwanted or promotional email, scams, or irrelevant content\n"
        context += "2. urgent - Time-sensitive or critical matter requiring immediate attention\n"
        context += "3. business - Professional or work-related correspondence\n"
        context += "4. friendly - Personal, social, or positive in nature\n"
        context += "5. complaint - Expressing dissatisfaction or raising an issue\n\n"
        context += "".join(email_texts)
        context += "\nReturn classifications in JSON format: {\"classifications\": [{\"email_index\": 1, \"tag\": \"urgent\"}, ...]}"
        

        for i, email in enumerate(emails_to_process):
            context += (
                f"Email {i+1}:\nFrom: {email['sender']}\n"
                f"Subject: {email['subject']}\n"
                f"Snippet: {email['body'][:150]}...\n\n"
            )

        context += (
            'Return classifications in JSON format:\n'
            '{"classifications": [{"email_index": 1, "tag": "spam"}, ...]}'
        )

        try:
            # Call OpenAI to classify emails
            resp = self.client.chat.completions.create(
                model="gpt-4o-mini-2024-07-18",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that classifies emails by intent and sentiment."},
                    {"role": "user", "content": context}
                ],
                response_format={"type": "json_object"},
                temperature=0.3
            )
            
            # Parse the response
            result = resp.choices[0].message.content
            # Add error handling for JSON parsing if needed
            import json
            classifications = json.loads(result).get("classifications", [])
            
            # Assign the tags back to the original emails
            for classification in classifications:
                email_index = classification.get("email_index") - 1  # Convert to 0-indexed
                tag = classification.get("tag")
                if 0 <= email_index < len(emails_to_process):
                    emails_to_process[email_index]["tag"] = tag
            
            # Ensure all processed emails have a tag (default to 'default' if missing)
            for email in emails_to_process:
                if "tag" not in email:
                    email["tag"] = "default"
                    
            return emails_to_process
            
        except Exception as e:
            # On error, return the original emails with default tags
            for email in emails_to_process:
                email["tag"] = "default"  # Default tag
            print(f"Error classifying emails: {e}")
            return emails_to_process
        
    def is_spam(self, email):
        """
        Simple keyword-based spam detection.
        Flags emails that contain common spammy words in subject/body.
        """
        spam_keywords = [
            "unsubscribe", "promotion", "deal", "special offer", "limited time", 
            "buy now", "discount", "click here", "free", "winner", "congratulations"
        ]
        subject = email.get("subject", "").lower()
        body = email.get("body", "").lower()
        
        return any(kw in subject or kw in body for kw in spam_keywords)
            
    def get_emoji_for_tag(self, tag):
        emoji_map = {
            "spam": "🚫",
            "urgent": "⚠️",
            "business": "💼",
            "friendly": "😊",
            "complaint": "😡",
            "default": " "
        }
        return emoji_map.get(tag, "")