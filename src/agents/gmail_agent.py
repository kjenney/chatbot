"""
Gmail Agent
Fetches and summarizes recent emails using Gmail API with OAuth2
"""

import os
from typing import Dict, Any, List, Optional
from agents.base_agent import BaseAgent

SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
CREDENTIALS_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'gmail_credentials.json')
TOKEN_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'gmail_token.json')


class GmailAgent(BaseAgent):
    """Sub-agent to fetch and return recent Gmail emails"""

    def __init__(self):
        super().__init__(
            name="gmail",
            description="Fetches recent emails from Gmail inbox"
        )

    def execute(self, max_emails: int = 10, query: str = 'is:unread', **kwargs) -> Dict[str, Any]:
        """
        Fetch recent emails from Gmail.

        Args:
            max_emails: Maximum number of emails to fetch
            query: Gmail search query (default: unread emails)
        """
        try:
            service = self._get_gmail_service()
            if not service:
                return {
                    'success': False,
                    'error': (
                        'Gmail not authenticated. Create gmail_credentials.json from '
                        'Google Cloud Console and run the chatbot once interactively to authorize.'
                    )
                }

            results = service.users().messages().list(
                userId='me',
                q=query,
                maxResults=max_emails
            ).execute()

            messages = results.get('messages', [])
            if not messages:
                return {'success': True, 'data': {'emails': [], 'count': 0, 'query': query}}

            emails = []
            for msg in messages:
                detail = service.users().messages().get(
                    userId='me',
                    id=msg['id'],
                    format='metadata',
                    metadataHeaders=['From', 'Subject', 'Date']
                ).execute()

                headers = {h['name']: h['value'] for h in detail.get('payload', {}).get('headers', [])}
                snippet = detail.get('snippet', '')

                emails.append({
                    'id': msg['id'],
                    'from': headers.get('From', 'Unknown'),
                    'subject': headers.get('Subject', '(no subject)'),
                    'date': headers.get('Date', ''),
                    'snippet': snippet[:300],
                })

            return {
                'success': True,
                'data': {
                    'emails': emails,
                    'count': len(emails),
                    'query': query,
                }
            }

        except Exception as e:
            return {'success': False, 'error': f"Gmail fetch failed: {str(e)}"}

    def _get_gmail_service(self):
        """Build and return authenticated Gmail API service."""
        try:
            from google.oauth2.credentials import Credentials
            from google.auth.transport.requests import Request
            from googleapiclient.discovery import build
        except ImportError:
            return None

        creds = None

        if os.path.exists(TOKEN_FILE):
            creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not os.path.exists(CREDENTIALS_FILE):
                    return None
                from google_auth_oauthlib.flow import InstalledAppFlow
                flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
                creds = flow.run_local_server(port=0)

            with open(TOKEN_FILE, 'w') as f:
                f.write(creds.to_json())

        return build('gmail', 'v1', credentials=creds)
