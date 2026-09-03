import base64
from email.message import EmailMessage

from app.config import Settings


class GmailError(RuntimeError):
    pass


def send_approved_email(settings: Settings, *, recipient: str, subject: str, body: str) -> str:
    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build
    except ImportError as exc:
        raise GmailError("Gmail dependencies are not installed") from exc

    scopes = ["https://www.googleapis.com/auth/gmail.send"]
    credentials = None
    try:
        credentials = Credentials.from_authorized_user_file(settings.gmail_token_file, scopes)
    except FileNotFoundError:
        pass
    if not credentials or not credentials.valid:
        if credentials and credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(settings.gmail_credentials_file, scopes)
            credentials = flow.run_local_server(port=0)
        with open(settings.gmail_token_file, "w", encoding="utf-8") as token:
            token.write(credentials.to_json())

    message = EmailMessage()
    message["To"] = recipient
    message["Subject"] = subject
    message.set_content(body)
    encoded = base64.urlsafe_b64encode(message.as_bytes()).decode()
    sent = build("gmail", "v1", credentials=credentials).users().messages().send(
        userId="me", body={"raw": encoded}
    ).execute()
    return str(sent["id"])