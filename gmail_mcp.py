"""
gmail_mcp.py
------------
FastMCP server exposing Gmail as MCP tools:
  - list_inbox   : list recent emails
  - read_email   : read a full email thread
  - save_draft   : save a reply as a Gmail draft
  - send_email   : send an email directly (use carefully)

Run standalone:
    python gmail_mcp.py

Or import tools directly in agent.py (no server needed for local use).
"""

import os
import base64
import json
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv
from fastmcp import FastMCP
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

load_dotenv()

# OAuth scopes — gmail.modify allows read + draft + send
SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]
TOKEN_FILE = "token.json"
CREDENTIALS_FILE = "credentials.json"

mcp = FastMCP("gmail-email-assistant")


# ─────────────────────────────────────────────
# Gmail service helper
# ─────────────────────────────────────────────

def get_gmail_service():
    """
    Authenticate and return Gmail API service.
    On first run: opens browser for OAuth consent.
    Subsequent runs: loads token from token.json.
    """
    creds = None

    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(CREDENTIALS_FILE):
                raise FileNotFoundError(
                    f"'{CREDENTIALS_FILE}' not found.\n"
                    "Download it from Google Cloud Console:\n"
                    "  APIs & Services → Credentials → OAuth 2.0 Client IDs → Download JSON\n"
                    "Rename to 'credentials.json' and place in project root."
                )
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, "w") as f:
            f.write(creds.to_json())

    return build("gmail", "v1", credentials=creds)


def _decode_body(payload: dict) -> str:
    """Recursively extract plain text body from email payload."""
    body = ""
    if payload.get("mimeType") == "text/plain":
        data = payload.get("body", {}).get("data", "")
        if data:
            body = base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")
    elif "parts" in payload:
        for part in payload["parts"]:
            body += _decode_body(part)
    return body


def _headers_dict(headers: list) -> dict:
    return {h["name"]: h["value"] for h in headers}


# ─────────────────────────────────────────────
# MCP Tools
# ─────────────────────────────────────────────

@mcp.tool()
def list_inbox(max_results: int = 10, unread_only: bool = False) -> list[dict]:
    """
    List recent emails from the Gmail inbox.

    Args:
        max_results: Number of emails to return (default 10, max 50).
        unread_only: If True, return only unread emails.

    Returns:
        List of dicts with id, subject, from, date, snippet, is_read.
    """
    service = get_gmail_service()
    query = "is:unread" if unread_only else ""
    label_ids = ["INBOX"]

    try:
        response = service.users().messages().list(
            userId="me",
            labelIds=label_ids,
            maxResults=min(max_results, 50),
            q=query,
        ).execute()
    except HttpError as e:
        return [{"error": str(e)}]

    messages = response.get("messages", [])
    result = []

    for msg in messages:
        try:
            detail = service.users().messages().get(
                userId="me",
                id=msg["id"],
                format="metadata",
                metadataHeaders=["Subject", "From", "Date"],
            ).execute()
            h = _headers_dict(detail["payload"]["headers"])
            labels = detail.get("labelIds", [])
            result.append({
                "id": msg["id"],
                "subject": h.get("Subject", "(no subject)"),
                "from": h.get("From", "unknown"),
                "date": h.get("Date", ""),
                "snippet": detail.get("snippet", ""),
                "is_read": "UNREAD" not in labels,
            })
        except HttpError:
            continue

    return result


@mcp.tool()
def read_email(message_id: str) -> dict:
    """
    Read the full content of an email by its message ID.

    Args:
        message_id: Gmail message ID (from list_inbox).

    Returns:
        Dict with id, subject, from, to, date, body, thread_id.
    """
    service = get_gmail_service()
    try:
        msg = service.users().messages().get(
            userId="me",
            id=message_id,
            format="full",
        ).execute()
    except HttpError as e:
        return {"error": str(e)}

    payload = msg["payload"]
    h = _headers_dict(payload.get("headers", []))
    body = _decode_body(payload)

    # Mark as read
    try:
        service.users().messages().modify(
            userId="me",
            id=message_id,
            body={"removeLabelIds": ["UNREAD"]},
        ).execute()
    except HttpError:
        pass

    return {
        "id": message_id,
        "thread_id": msg.get("threadId", ""),
        "subject": h.get("Subject", "(no subject)"),
        "from": h.get("From", "unknown"),
        "to": h.get("To", ""),
        "date": h.get("Date", ""),
        "body": body.strip(),
    }


@mcp.tool()
def save_draft(
    to: str,
    subject: str,
    body: str,
    reply_to_id: str = "",
) -> dict:
    """
    Save a reply as a Gmail draft (does NOT send).

    Args:
        to: Recipient email address.
        subject: Email subject line.
        body: Plain text body of the reply.
        reply_to_id: Optional message ID to thread the reply under.

    Returns:
        Dict with draft_id and status.
    """
    service = get_gmail_service()

    msg = MIMEMultipart()
    msg["To"] = to
    msg["Subject"] = subject
    if reply_to_id:
        msg["In-Reply-To"] = reply_to_id
        msg["References"] = reply_to_id
    msg.attach(MIMEText(body, "plain"))

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")
    draft_body = {"message": {"raw": raw}}
    if reply_to_id:
        # Attach to existing thread if possible
        try:
            orig = service.users().messages().get(
                userId="me", id=reply_to_id, format="metadata"
            ).execute()
            draft_body["message"]["threadId"] = orig.get("threadId", "")
        except HttpError:
            pass

    try:
        draft = service.users().drafts().create(
            userId="me", body=draft_body
        ).execute()
        return {
            "draft_id": draft["id"],
            "status": "saved",
            "message": "Draft saved to Gmail. Open Gmail to review and send.",
        }
    except HttpError as e:
        return {"error": str(e), "status": "failed"}


@mcp.tool()
def send_email(to: str, subject: str, body: str) -> dict:
    """
    Send an email directly (bypasses draft — use with caution).

    Args:
        to: Recipient email address.
        subject: Subject line.
        body: Plain text body.

    Returns:
        Dict with message_id and status.
    """
    service = get_gmail_service()

    msg = MIMEText(body, "plain")
    msg["To"] = to
    msg["Subject"] = subject

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")

    try:
        sent = service.users().messages().send(
            userId="me", body={"raw": raw}
        ).execute()
        return {"message_id": sent["id"], "status": "sent"}
    except HttpError as e:
        return {"error": str(e), "status": "failed"}


@mcp.tool()
def search_emails(query: str, max_results: int = 5) -> list[dict]:
    """
    Search Gmail with a query string (same syntax as Gmail search bar).

    Args:
        query: Gmail search string, e.g. 'from:boss@company.com subject:budget'
        max_results: Max emails to return.

    Returns:
        List of email summaries matching the query.
    """
    service = get_gmail_service()
    try:
        response = service.users().messages().list(
            userId="me",
            q=query,
            maxResults=min(max_results, 20),
        ).execute()
    except HttpError as e:
        return [{"error": str(e)}]

    messages = response.get("messages", [])
    result = []
    for msg in messages:
        try:
            detail = service.users().messages().get(
                userId="me",
                id=msg["id"],
                format="metadata",
                metadataHeaders=["Subject", "From", "Date"],
            ).execute()
            h = _headers_dict(detail["payload"]["headers"])
            result.append({
                "id": msg["id"],
                "subject": h.get("Subject", "(no subject)"),
                "from": h.get("From", "unknown"),
                "date": h.get("Date", ""),
                "snippet": detail.get("snippet", ""),
            })
        except HttpError:
            continue
    return result


if __name__ == "__main__":
    print("Starting Gmail MCP server (stdio transport)...")
    mcp.run(transport="stdio")
