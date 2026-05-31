"""
app.py
------
Streamlit UI for the AI Email Assistant.

Run:
    streamlit run app.py
"""

import os
import re
import streamlit as st
from dotenv import load_dotenv
from gmail_mcp import list_inbox, read_email, save_draft
from rag_chain import draft_reply

load_dotenv()


def extract_email(from_field: str) -> str:
    """Extract plain email address from a 'Name <email>' style string."""
    match = re.search(r'[\w\.-]+@[\w\.-]+', from_field)
    return match.group(0) if match else from_field


# ─────────────────────────────────────────────
# Page config
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="AI Email Assistant",
    page_icon="✉️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────
# Custom CSS
# ─────────────────────────────────────────────
st.markdown("""
<style>
    .main-header {
        font-size: 1.6rem;
        font-weight: 600;
        margin-bottom: 0;
    }
    .sub-header {
        font-size: 0.85rem;
        color: #888;
        margin-top: 0;
        margin-bottom: 1.5rem;
    }
    .email-card {
        border: 1px solid #e0e0e0;
        border-radius: 8px;
        padding: 12px 16px;
        margin-bottom: 8px;
        cursor: pointer;
        transition: border-color 0.2s;
    }
    .email-card:hover { border-color: #1a73e8; }
    .source-badge {
        display: inline-block;
        background: #e8f0fe;
        color: #1a73e8;
        font-size: 0.75rem;
        padding: 2px 8px;
        border-radius: 12px;
        margin-right: 4px;
    }
    .chunk-box {
        background: #f8f9fa;
        border-left: 3px solid #1a73e8;
        padding: 8px 12px;
        font-size: 0.82rem;
        color: #555;
        border-radius: 0 4px 4px 0;
        margin-bottom: 6px;
    }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# Session state defaults
# ─────────────────────────────────────────────
if "emails" not in st.session_state:
    st.session_state.emails = []
if "selected_id" not in st.session_state:
    st.session_state.selected_id = None
if "selected_email" not in st.session_state:
    st.session_state.selected_email = None
if "draft_result" not in st.session_state:
    st.session_state.draft_result = None
if "draft_saved" not in st.session_state:
    st.session_state.draft_saved = False

# ─────────────────────────────────────────────
# Sidebar
# ─────────────────────────────────────────────
with st.sidebar:
    st.markdown("### ⚙️ Settings")
    max_emails = st.slider("Emails to load", 5, 30, 10)
    unread_only = st.toggle("Unread only", value=True)
    model_label = st.selectbox(
        "Groq model",
        ["llama-3.3-70b-versatile", "llama-3.1-8b-instant", "mixtral-8x7b-32768"],
    )
    os.environ["GROQ_MODEL"] = model_label

    st.divider()

    if st.button("🔄 Refresh inbox", use_container_width=True):
        with st.spinner("Loading inbox..."):
            try:
                st.session_state.emails = list_inbox(
                    max_results=max_emails, unread_only=unread_only
                )
                st.session_state.selected_id = None
                st.session_state.selected_email = None
                st.session_state.draft_result = None
            except Exception as e:
                st.error(f"Gmail error: {e}")

    st.divider()
    st.markdown("**Stack**")
    st.markdown("- 🟣 Groq (Llama-3.3-70b)")
    st.markdown("- 🔵 LangChain + ChromaDB")
    st.markdown("- 🟢 Gmail API (MCP tools)")
    st.markdown("- 🟠 FastAPI + Streamlit")


# ─────────────────────────────────────────────
# Main layout
# ─────────────────────────────────────────────
st.markdown('<p class="main-header">✉️ AI Email Assistant</p>', unsafe_allow_html=True)
st.markdown(
    '<p class="sub-header">Groq + RAG over company knowledge base</p>',
    unsafe_allow_html=True,
)

col_inbox, col_compose = st.columns([1, 2], gap="medium")

# ─── Left: Inbox ───
with col_inbox:
    st.markdown("#### Inbox")

    if not st.session_state.emails:
        st.info("Click **Refresh inbox** in the sidebar to load emails.")
    else:
        for email in st.session_state.emails:
            is_selected = email["id"] == st.session_state.selected_id
            unread_dot = "🔵 " if not email.get("is_read") else ""

            label = f"{unread_dot}{email['subject'][:42]}"
            from_line = email['from'][:35]

            if st.button(
                f"{label}\n{from_line}",
                key=f"email_{email['id']}",
                use_container_width=True,
            ):
                with st.spinner("Reading email..."):
                    full_email = read_email(email["id"])
                    st.session_state.selected_id = email["id"]
                    st.session_state.selected_email = full_email
                    st.session_state.draft_result = None
                    st.session_state.draft_saved = False
                st.rerun()


# ─── Right: Email + Draft ───
with col_compose:
    if st.session_state.selected_email is None:
        st.markdown(
            "<div style='text-align:center;color:#aaa;margin-top:80px'>"
            "<div style='font-size:3rem'>✉️</div>"
            "<div>Select an email from the inbox</div>"
            "</div>",
            unsafe_allow_html=True,
        )
    else:
        email = st.session_state.selected_email

        # Email header
        st.markdown(f"### {email.get('subject', '(no subject)')}")
        col_a, col_b = st.columns(2)
        col_a.caption(f"**From:** {email.get('from', '')}")
        col_b.caption(f"**Date:** {email.get('date', '')}")

        # Original email body
        with st.expander("📧 Original email", expanded=True):
            st.text(email.get("body", "(empty)"))

        st.divider()

        # Generate draft button
        if st.button("✨ Generate draft with Groq", type="primary", use_container_width=True):
            if not email.get("body", "").strip():
                st.warning("Email body is empty — nothing to reply to.")
            else:
                with st.spinner("Retrieving context + generating with Groq..."):
                    try:
                        result = draft_reply(email["body"])
                        st.session_state.draft_result = result
                        st.session_state.draft_saved = False
                    except Exception as e:
                        st.error(f"Generation error: {e}")

        # Show draft
        if st.session_state.draft_result:
            result = st.session_state.draft_result

            st.markdown("#### 📝 Generated Draft")

            # Source badges
            if result["sources"]:
                badges = " ".join(
                    f'<span class="source-badge">📄 {s}</span>'
                    for s in result["sources"]
                )
                st.markdown(
                    f"<div style='margin-bottom:8px'>Grounded in: {badges}</div>",
                    unsafe_allow_html=True,
                )

            # Editable draft
            edited_draft = st.text_area(
                "Edit before saving:",
                value=result["draft"],
                height=200,
                key="draft_editor",
            )

            # Retrieved chunks (debug/resume showcase)
            with st.expander("🔍 Retrieved knowledge chunks", expanded=False):
                for chunk in result.get("chunks", []):
                    st.markdown(
                        f'<div class="chunk-box">'
                        f'<strong>{chunk["source"]}</strong> (p.{chunk["page"]})<br>'
                        f'{chunk["content"]}'
                        f"</div>",
                        unsafe_allow_html=True,
                    )

            # Save button
            col_save, col_discard = st.columns([2, 1])
            with col_save:
                if st.button(
                    "💾 Save to Gmail drafts",
                    use_container_width=True,
                    disabled=st.session_state.draft_saved,
                ):
                    with st.spinner("Saving draft to Gmail..."):
                        try:
                            resp = save_draft(
                                to=extract_email(email["from"]),
                                subject=f"Re: {email.get('subject', '')}",
                                body=edited_draft,
                                reply_to_id=email["id"],
                            )
                            if resp.get("status") == "saved":
                                st.session_state.draft_saved = True
                                st.success(
                                    f"Draft saved! (ID: {resp.get('draft_id', '')})\n"
                                    "Open Gmail to review and send."
                                )
                            else:
                                st.error(f"Save failed: {resp.get('error')}")
                        except Exception as e:
                            st.error(f"Error: {e}")

            with col_discard:
                if st.button("🗑️ Discard", use_container_width=True):
                    st.session_state.draft_result = None
                    st.session_state.draft_saved = False
                    st.rerun()