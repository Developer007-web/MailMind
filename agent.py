"""
agent.py
--------
Main orchestrator: reads inbox → drafts reply via RAG+Groq → saves to Gmail.

Usage:
    # List inbox and process emails interactively
    python agent.py

    # Auto-save drafts without prompting
    python agent.py --auto

    # Process a specific number of emails
    python agent.py --count 5
"""

import argparse
import sys
from dotenv import load_dotenv
from gmail_mcp import list_inbox, read_email, save_draft
from rag_chain import draft_reply

load_dotenv()

SEPARATOR = "─" * 60


def print_email(email: dict):
    print(f"\n{SEPARATOR}")
    print(f"  Subject : {email.get('subject', '')}")
    print(f"  From    : {email.get('from', '')}")
    print(f"  Date    : {email.get('date', '')}")
    print(f"{SEPARATOR}")
    body = email.get("body", "")
    preview = body[:500] + ("..." if len(body) > 500 else "")
    print(preview)


def print_draft(result: dict):
    print(f"\n{'─'*60}")
    print("  GENERATED DRAFT")
    print(f"{'─'*60}")
    print(result["draft"])
    print(f"\n  Sources: {', '.join(result['sources']) or 'none'}")
    if result.get("chunks"):
        print(f"\n  Retrieved chunks:")
        for c in result["chunks"]:
            print(f"    • [{c['source']} p.{c['page']}] {c['content'][:100]}...")


def process_email(email: dict, auto_save: bool = False) -> dict:
    """Process a single email: generate draft and optionally save."""
    print(f"\nProcessing: {email.get('subject', '')}")
    print("Retrieving context and generating draft via Groq...")

    result = draft_reply(email["body"])
    print_draft(result)

    if auto_save:
        resp = save_draft(
            to=email["from"],
            subject=f"Re: {email['subject']}",
            body=result["draft"],
            reply_to_id=email["id"],
        )
        print(f"\n  ✓ {resp.get('message', resp)}")
        return {**result, "draft_saved": True, "draft_id": resp.get("draft_id")}

    # Interactive mode
    print("\n  [s] Save as draft  [e] Edit then save  [k] Skip  [q] Quit")
    choice = input("  Action: ").strip().lower()

    if choice == "s":
        resp = save_draft(
            to=email["from"],
            subject=f"Re: {email['subject']}",
            body=result["draft"],
            reply_to_id=email["id"],
        )
        print(f"  ✓ {resp.get('message', resp)}")
        return {**result, "draft_saved": True}

    elif choice == "e":
        print("\n  Paste your edited reply (type END on a new line when done):")
        lines = []
        while True:
            line = input()
            if line.strip() == "END":
                break
            lines.append(line)
        edited = "\n".join(lines)
        resp = save_draft(
            to=email["from"],
            subject=f"Re: {email['subject']}",
            body=edited,
            reply_to_id=email["id"],
        )
        print(f"  ✓ {resp.get('message', resp)}")
        return {**result, "draft_saved": True, "edited": True}

    elif choice == "q":
        print("Exiting.")
        sys.exit(0)
    else:
        print("  Skipped.")
        return {**result, "draft_saved": False}


def run(count: int = 5, auto_save: bool = False, unread_only: bool = True):
    print("\n══════════════════════════════════════════")
    print("  AI Email Assistant  |  Groq + RAG")
    print("══════════════════════════════════════════")

    print(f"\nFetching up to {count} {'unread ' if unread_only else ''}emails...")
    emails_meta = list_inbox(max_results=count, unread_only=unread_only)

    if not emails_meta or "error" in emails_meta[0]:
        print(f"Error fetching inbox: {emails_meta}")
        return

    print(f"Found {len(emails_meta)} emails.")

    for i, meta in enumerate(emails_meta, 1):
        print(f"\n[{i}/{len(emails_meta)}] {meta['subject'][:60]}")

        email = read_email(meta["id"])
        if "error" in email:
            print(f"  Error reading email: {email['error']}")
            continue

        if not email.get("body", "").strip():
            print("  Empty body — skipping.")
            continue

        process_email(email, auto_save=auto_save)

    print(f"\n{'─'*60}")
    print("Done. Open Gmail to review your drafts.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AI Email Assistant")
    parser.add_argument("--count", type=int, default=5, help="Number of emails to process")
    parser.add_argument("--auto", action="store_true", help="Auto-save drafts without prompting")
    parser.add_argument("--all", dest="all_emails", action="store_true", help="Include read emails")
    args = parser.parse_args()

    run(
        count=args.count,
        auto_save=args.auto,
        unread_only=not args.all_emails,
    )
