import os 
import base64
import re

# Google OAuth 2.0 and Authentication modules
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

# Google API Client module
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

gmail_dataset = []

def main():
    creds = None 

    # this file stores your access and refresh tokens after first logging in
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request()) # make new access token
        else:
            # opens webbrowser and reads credentials.json
            flow = InstalledAppFlow.from_client_secrets_file('transformers/credentials.json', SCOPES)
            creds = flow.run_local_server(port = 0)
    
        # saves the token so we dont have to log in every time
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    ####################################################################
    # now we actually build the service engine that let's us talk to Google
    service = build('gmail', 'v1', credentials = creds)

    # call list
    print('Fetching gmails...')

    # email address
    email_address = 'patrickming88@gmail.com'
    special_address = 'me'

    query = "-category:promotions -category:social -category:updates -unsubscribe"

    results = service.users().messages().list(
        userId = special_address, # usually this is an email, but 'me' is special!
        maxResults = 500,
        q=query
    ).execute()

    messages = results.get('messages', [])
    if not messages:
        print('no messages!')
        return

    # else
    print(f'Suceess! retrieved {len(messages)} message IDs')
    print(f'Most recent ID taken is {messages[-1]['id']}')

    for msg in messages:
        details = extract_information(service, msg['id'])

        if is_junk_email(details['sender'], details['subject']):
            continue

        clean_body = clean_boilerplate(details['body'])
        details['body'] = clean_body

        if not details['body']:
            continue

        gmail_dataset.append(details)
    

def extract_information(service, msg_id):
    msg = service.users().messages().get(
        userId='me', 
        id = msg_id, 
        format='full'
    ).execute()

    payload = msg['payload']
    headers = payload.get('headers', [])

    sender = ""
    subject = ""
    date = ""
    body = extract_body(payload)
    
    for header in headers:
        if header['name'].lower() == 'from':
            sender = header['value']
        elif header['name'].lower() == 'subject':
            subject = header['value']
        elif header['name'].lower() == 'date':
            date = header['value']

    return {
        "sender": sender,
        "subject": subject, 
        "date": date,
        "body": body
    }

def extract_body(payload):
    # base case: plain text:
    if payload.get('mimeType') == 'text/plain' and 'data' in payload.get('body', {}):
        data = payload['body']['data']

        data += '=' * ((4 - len(data) % 4) % 4)

        # decode url-safe base64 string into raw bytes
        clean_bytes = base64.urlsafe_b64decode(data)

        return clean_bytes.decode('utf-8', errors = 'ignore')
    # accounts for when email is broken into multiple parts: [text, html, attachments]
    elif 'parts' in payload:
        full_text = ''
        for part in payload['parts']:
            full_text += extract_body(part)
        return full_text

    # last case, email is devoid of text, i.e. just html or image or etc.
    return ""

def is_junk_email(sender, subject):
    """
    Checks the sender and subject for obvious signs of automated/junk mail
    that slipped past the Gmail API filter.
    """
    sender_lower = sender.lower()
    subject_lower = subject.lower()
    
    # Catch automated sender addresses
    if "no-reply" in sender_lower or "donotreply" in sender_lower or "mailer-daemon" in sender_lower:
        return True
        
    # Catch straggler marketing/spam subjects
    spam_keywords = ["exclusive offer", "promo code", "rewards", "trouble viewing"]
    if any(keyword in subject_lower for keyword in spam_keywords):
        return True
        
    return False

def clean_boilerplate(text):
    """
    Uses Regular Expressions (re) to chop off repetitive signatures, 
    device tags, and massive forwarding histories.
    """
    # 1. Remove "Sent from my..." device tags
    # (?i) makes it case-insensitive. .* catches everything after it on that line.
    text = re.sub(r'(?i)sent from my (iphone|ipad|android|mobile device).*', '', text)
    text = re.sub(r'(?i)get outlook for ios.*', '', text)
    
    # 2. Chop off forwarded message histories
    text = re.sub(r'(?i)-+original message-+.*', '', text, flags=re.DOTALL)
    text = re.sub(r'(?i)on .*? wrote:.*', '', text, flags=re.DOTALL)
    text = re.sub(r'(?i)forwarded message.*', '', text, flags=re.DOTALL)
    
    # 3. Remove common institutional/corporate disclaimers
    text = re.sub(r'(?i)caution: this email originated from outside.*', '', text)
    
    # 4. Clean up the messy empty lines left behind by the deletions
    text = re.sub(r'\n{3,}', '\n\n', text).strip()
    
    return text

if __name__ == "__main__":
    main()