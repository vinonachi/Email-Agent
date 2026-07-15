import html
import pickle
import re
from pathlib import Path

from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
TOKEN_FILE = Path('token.pickle')


def get_gmail_service():
    """
    Returns an authenticated Gmail API service.

    First run: opens the browser for OAuth consent, then saves the
    resulting credentials to token.pickle.

    Every run after that: loads token.pickle and silently refreshes
    the access token in the background (no browser popup) as long as
    the refresh token is still valid. The browser only reopens if
    token.pickle is missing, corrupted, or the refresh token itself
    has been revoked/expired.
    """
    creds = None

    if TOKEN_FILE.exists():
        try:
            with open(TOKEN_FILE, 'rb') as f:
                creds = pickle.load(f)
        except Exception:
            creds = None  # corrupted/unreadable cache — fall through to re-auth

    if creds and creds.valid:
        return build('gmail', 'v1', credentials=creds)

    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
        except Exception:
            creds = None  # refresh token revoked/expired — need fresh login

    if not creds or not creds.valid:
        flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
        creds = flow.run_local_server(port=0)

    with open(TOKEN_FILE, 'wb') as f:
        pickle.dump(creds, f)

    return build('gmail', 'v1', credentials=creds)


def _parse_headers(headers):
    subject = 'No Subject'
    sender = 'Unknown'
    for header in headers:
        name = header.get('name', '').lower()
        value = header.get('value', '')
        if name == 'subject':
            subject = value
        elif name == 'from':
            sender = value
    return subject, sender


def _split_sender(sender):
    match = re.search(r'^(.*?)(?:\s*<([^>]+)>)?$', sender.strip())
    if not match:
        return sender, sender

    name = match.group(1).strip().strip('"')
    email = match.group(2) or match.group(1)
    if '<' in sender and '>' in sender:
        name = name
    else:
        email = sender
    return (name or email, email)


def fetch_recent_emails(service, max_results=15):
    results = service.users().messages().list(userId='me', maxResults=max_results).execute()
    messages = results.get('messages', [])

    emails = []
    for msg in messages:
        message = service.users().messages().get(
            userId='me', id=msg['id'], format='metadata', metadataHeaders=['Subject', 'From']
        ).execute()

        headers = message.get('payload', {}).get('headers', [])
        subject, sender = _parse_headers(headers)
        sender_name, sender_email = _split_sender(sender)
        subject = html.unescape(subject)
        sender_name = html.unescape(sender_name)
        preview = html.unescape(message.get('snippet', ''))

        emails.append(
            {
                'id': message.get('id'),
                'sender_name': sender_name,
                'sender_email': sender_email,
                'subject': subject,
                'preview': preview,
            }
        )

    return emails
