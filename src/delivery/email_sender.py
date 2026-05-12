"""Sends newsletter email with PDF attachment via Gmail SMTP + App Password."""
from __future__ import annotations

import os
import re
import smtplib
import ssl
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path


def _strip_markdown(text: str) -> str:
    """Convert markdown to clean plain text for email body."""
    # Remove markdown links: [text](url) → text
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    # Remove bold: **text** → text
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
    # Remove italic: *text* → text
    text = re.sub(r"\*([^*]+)\*", r"\1", text)
    # Remove headers: ## Header → Header
    text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)
    # Remove horizontal rules
    text = re.sub(r"^---+\s*$", "─" * 40, text, flags=re.MULTILINE)
    # Clean up bullet points
    text = re.sub(r"^[•●]\s+", "  · ", text, flags=re.MULTILINE)
    text = re.sub(r"^[-*]\s+", "  · ", text, flags=re.MULTILINE)
    # Remove inline code backticks
    text = re.sub(r"`([^`]+)`", r"\1", text)
    return text.strip()


def _extract_preview(newsletter_md: str) -> str:
    """Extract a clean preview from the newsletter markdown."""
    lines = newsletter_md.strip().split("\n")
    preview_parts = []

    # Get the editorial intro (first italic paragraph)
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("*") and stripped.endswith("*") and not stripped.startswith("**"):
            preview_parts.append(_strip_markdown(stripped))
            break

    # Get The Wave Today first item headline
    in_wave = False
    for line in lines:
        stripped = line.strip()
        if "wave today" in stripped.lower() or "noticias que mueven" in stripped.lower():
            in_wave = True
            continue
        if in_wave and stripped.startswith("###"):
            preview_parts.append(_strip_markdown(stripped))
            break
        if in_wave and stripped.startswith("## ") and "wave" not in stripped.lower():
            break

    return "\n\n".join(preview_parts)


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
        print("[email] Get an App Password at: myaccount.google.com > Security > App passwords")
        return False

    type_label = "Weekly" if newsletter_type == "weekly" else "Daily"
    subject = f"Surfing the AI Wave \u2014 {type_label} Brief ({date_str})"

    preview = _extract_preview(newsletter_md)

    body_text = (
        f"Surfing the AI Wave \u2014 {type_label} Brief\n"
        f"{date_str}\n\n"
        f"{preview}\n\n"
        f"{'─' * 40}\n"
        f"Briefing completo en el PDF adjunto.\n"
    )

    msg = MIMEMultipart()
    msg["From"] = sender
    msg["To"] = recipient
    msg["Subject"] = subject
    msg.attach(MIMEText(body_text, "plain", "utf-8"))

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
