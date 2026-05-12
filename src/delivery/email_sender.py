"""Sends newsletter email with PDF attachment via Gmail SMTP + App Password."""
from __future__ import annotations

import os
import smtplib
import ssl
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path


def send_newsletter_email(
    newsletter_md: str,
    pdf_path: str,
    recipient: str | None = None,
    date_str: str = "",
    newsletter_type: str = "daily",
) -> bool:
    """Send newsletter email with PDF attachment via Gmail SMTP."""
    recipient = recipient or os.getenv("NEWSLETTER_RECIPIENT", "")
    sender = os.getenv("GMAIL_ADDRESS", "")
    app_password = os.getenv("GMAIL_APP_PASSWORD", "")

    if not recipient:
        print("[email] No recipient configured. Set NEWSLETTER_RECIPIENT env var.")
        return False
    if not sender or not app_password:
        print("[email] Gmail credentials missing. Set GMAIL_ADDRESS and GMAIL_APP_PASSWORD env vars.")
        print("[email] Get an App Password at: myaccount.google.com → Security → App passwords")
        return False

    subject = f"Surfing the AI Wave — {newsletter_type.capitalize()} Brief ({date_str})"

    # Extract intro lines as plain-text body preview
    lines = newsletter_md.strip().split("\n")
    preview_lines = []
    for line in lines[:20]:
        if line.strip() and not line.startswith("#"):
            preview_lines.append(line.strip())
        if len(preview_lines) >= 5:
            break

    body_text = (
        f"Surfing the AI Wave — {newsletter_type.capitalize()} Brief\n"
        f"{date_str}\n\n"
        + "\n".join(preview_lines)
        + "\n\n---\nFull briefing attached as PDF.\n"
    )

    msg = MIMEMultipart()
    msg["From"] = sender
    msg["To"] = recipient
    msg["Subject"] = subject
    msg.attach(MIMEText(body_text, "plain"))

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
        print(f"[email] PDF not found at {pdf_path}, sending without attachment.")

    try:
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
            server.login(sender, app_password)
            server.sendmail(sender, recipient, msg.as_string())
        print(f"[email] Newsletter sent to {recipient}")
        return True
    except smtplib.SMTPAuthenticationError:
        print("[email] Authentication failed. Check GMAIL_ADDRESS and GMAIL_APP_PASSWORD.")
        print("[email] Make sure you're using an App Password, not your regular Gmail password.")
        return False
    except Exception as e:
        print(f"[email] Failed to send: {e}")
        return False
