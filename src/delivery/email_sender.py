"""Sends newsletter email with PDF attachment via Gmail API."""
from __future__ import annotations

import base64
import os
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build


def send_newsletter_email(
    newsletter_md: str,
    pdf_path: str,
    recipient: str | None = None,
    date_str: str = "",
    newsletter_type: str = "daily",
) -> bool:
    """Send newsletter email with PDF attachment via Gmail API."""
    recipient = recipient or os.getenv("NEWSLETTER_RECIPIENT", "")
    if not recipient:
        print("[email] No recipient configured. Set NEWSLETTER_RECIPIENT env var.")
        return False

    # Build Gmail service
    creds = _get_credentials()
    if not creds:
        print("[email] No Gmail credentials found.")
        return False

    service = build("gmail", "v1", credentials=creds)

    # Compose email
    subject = f"🏄 Surfing the AI Wave — {newsletter_type.capitalize()} Brief ({date_str})"

    # Extract first few lines as email preview
    lines = newsletter_md.strip().split("\n")
    preview_lines = []
    for line in lines[:20]:
        if line.strip() and not line.startswith("#"):
            preview_lines.append(line.strip())
        if len(preview_lines) >= 5:
            break
    preview = "\n".join(preview_lines)

    body_text = f"""Surfing the AI Wave — {newsletter_type.capitalize()} Brief
{date_str}

{preview}

---
Full briefing attached as PDF.
"""

    msg = MIMEMultipart()
    msg["To"] = recipient
    msg["Subject"] = subject
    msg.attach(MIMEText(body_text, "plain"))

    # Attach PDF
    pdf_file = Path(pdf_path)
    if pdf_file.exists():
        with open(pdf_file, "rb") as f:
            attachment = MIMEApplication(f.read(), _subtype="pdf")
            attachment.add_header(
                "Content-Disposition", "attachment",
                filename=f"surfing-ai-wave-{date_str}.pdf",
            )
            msg.attach(attachment)
    else:
        print(f"[email] PDF not found at {pdf_path}")

    # Send
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    try:
        service.users().messages().send(
            userId="me",
            body={"raw": raw},
        ).execute()
        print(f"[email] Newsletter sent to {recipient}")
        return True
    except Exception as e:
        print(f"[email] Failed to send: {e}")
        return False


def _get_credentials() -> Credentials | None:
    """Load Gmail OAuth2 credentials from environment or token file."""
    token_path = os.getenv("GMAIL_TOKEN_PATH", "config/gmail_token.json")

    if Path(token_path).exists():
        creds = Credentials.from_authorized_user_file(
            token_path,
            scopes=["https://www.googleapis.com/auth/gmail.send"],
        )
        if creds and creds.valid:
            return creds
        if creds and creds.expired and creds.refresh_token:
            from google.auth.transport.requests import Request
            creds.refresh(Request())
            # Save refreshed token
            Path(token_path).write_text(creds.to_json())
            return creds

    # Try environment variables
    access_token = os.getenv("GMAIL_ACCESS_TOKEN")
    refresh_token = os.getenv("GMAIL_REFRESH_TOKEN")
    client_id = os.getenv("GMAIL_CLIENT_ID")
    client_secret = os.getenv("GMAIL_CLIENT_SECRET")

    if all([refresh_token, client_id, client_secret]):
        creds = Credentials(
            token=access_token,
            refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=client_id,
            client_secret=client_secret,
            scopes=["https://www.googleapis.com/auth/gmail.send"],
        )
        if creds.expired:
            from google.auth.transport.requests import Request
            creds.refresh(Request())
        return creds

    return None
