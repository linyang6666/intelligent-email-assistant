from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import base64
import email

class GmailConnector:
    def __init__(self):
        self.SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
        self.service = None
    
    def authenticate(self):
        """Authenticate with Gmail API using OAuth2"""
        flow = InstalledAppFlow.from_client_secrets_file(
            'credentials.json', self.SCOPES)
        credentials = flow.run_local_server(port=0)
        self.service = build('gmail', 'v1', credentials=credentials)
        
    def get_recent_emails(self, max_emails=100):
        """Retrieve the most recent emails from Gmail"""
        if not self.service:
            raise Exception("Authentication required before fetching emails")
            
        results = self.service.users().messages().list(
            userId='me', maxResults=max_emails).execute()
        messages = results.get('messages', [])
        
        emails = []
        for message in messages:
            msg = self.service.users().messages().get(
                userId='me', id=message['id'], format='full').execute()
            
            # Extract email content
            payload = msg['payload']
            headers = payload['headers']
            
            # Get subject and sender
            subject = ''
            sender = ''
            for header in headers:
                if header['name'] == 'Subject':
                    subject = header['value']
                elif header['name'] == 'From':
                    sender = header['value']
            
            # Get body
            body = self._get_body(payload)
            
            emails.append({
                'id': message['id'],
                'subject': subject,
                'sender': sender,
                'body': body,
                'date': msg['internalDate']
            })
            
        return emails
    
    def _get_body(self, payload):
        """Extract the email body from the payload"""
        if 'parts' in payload:
            for part in payload['parts']:
                if part['mimeType'] == 'text/plain':
                    data = part['body'].get('data', '')
                    return base64.urlsafe_b64decode(data).decode('utf-8')
                elif 'parts' in part:
                    return self._get_body(part)
        elif 'body' in payload and 'data' in payload['body']:
            data = payload['body'].get('data', '')
            return base64.urlsafe_b64decode(data).decode('utf-8')
        
        return ''