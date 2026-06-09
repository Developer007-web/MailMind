# AI Email Assistant
### RAG + MCP + Groq · Python · LangChain · ChromaDB · Gmail API

An AI assistant that reads your Gmail inbox, retrieves relevant context from your company knowledge base using RAG, and drafts grounded replies using Groq (Llama-3.3-70b) — all without hallucinating policies that don't exist.

---

## Architecture

```
Gmail Inbox
    │
    ▼ MCP (list_inbox / read_email)
Email body
    │
    ▼ RAG (ChromaDB + MMR retrieval)
Top-4 relevant chunks from company docs
    │
    ▼ Groq LLM (llama-3.3-70b-versatile, temp=0.2)
Grounded email draft + source citations
    │
    ▼ MCP (save_draft)
Gmail Drafts folder (human reviews before sending)
```

## Stack

| Layer | Tool |
|---|---|
| LLM | Groq `llama-3.3-70b-versatile` (~300 tok/s) |
| RAG framework | LangChain `RetrievalQA` |
| Vector store | ChromaDB (local, persisted) |
| Embeddings | OpenAI `text-embedding-3-small` |
| Gmail integration | FastMCP + Gmail API (OAuth2) |
| API layer | FastAPI + uvicorn |
| UI | Streamlit |

---

## Setup

### 1. Clone and install

```bash
git clone https://github.com/yourname/email-assistant
cd email-assistant
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env and fill in:
#   GROQ_API_KEY   — from https://console.groq.com (free)
#   OPENAI_API_KEY — from https://platform.openai.com (for embeddings only)
```

### 3. Add company documents

Drop your PDF, DOCX, TXT, or MD files into `company_docs/`:

```
company_docs/
├── refund-policy.pdf
├── pricing.pdf
├── hr-handbook.pdf
├── product-faq.md
└── support-guide.txt
```

Then run the ingestion pipeline:

```bash
python ingest.py
```

This creates `chroma_db/` with all embedded chunks. Re-run whenever you add or update docs.

### 4. Set up Gmail OAuth

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a project → Enable **Gmail API**
3. Go to **APIs & Services → Credentials → Create Credentials → OAuth 2.0 Client ID**
4. Application type: **Desktop app**
5. Download the JSON → rename to `credentials.json` → place in project root
6. First run opens a browser window for consent — approve it
7. A `token.json` is saved automatically for future runs

### 5. Run

**Option A — Streamlit UI (recommended):**
```bash
streamlit run app.py
```

**Option B — CLI agent:**
```bash
# Interactive mode (review each draft before saving)
python agent.py

# Auto-save all drafts
python agent.py --auto --count 10

# Process all emails (not just unread)
python agent.py --all
```

**Option C — Direct Python:**
```python
from rag_chain import draft_reply
result = draft_reply("Can you clarify the refund policy for annual subscriptions?")
print(result["draft"])
print(result["sources"])
```

---

## Evaluation

Run the retrieval eval to measure RAG quality (edit `TEST_CASES` in `eval.py` to match your docs first):

```bash
python eval.py
```

Sample output:
```
  [✓] What is the refund policy for annual subscriptions?...
       Expected : refund-policy.pdf
       Retrieved: refund-policy.pdf, pricing.pdf
       Top score: 0.8912

  Precision@4: 4/5 = 80.0%
  ✓ Good retrieval quality (≥80%)
```

---

## Project structure

```
email-assistant/
├── ingest.py          # Load → chunk → embed → persist to ChromaDB
├── rag_chain.py       # Retrieval + Groq generation chain
├── gmail_mcp.py       # FastMCP server (Gmail tools)
├── agent.py           # CLI orchestrator
├── app.py             # Streamlit UI
├── eval.py            # Retrieval precision evaluation
├── requirements.txt
├── .env.example
├── company_docs/      # Your documents (add files here)
├── chroma_db/         # Auto-created after ingest.py
├── credentials.json   # Gmail OAuth credentials (you add this)
└── token.json         # Auto-created after first Gmail auth
```

---

## Key design decisions 

**Why Groq instead of OpenAI for generation?**
Groq runs Llama-3 at ~300 tokens/sec — replies are near-instant. For a demo, this is far more impressive than waiting 3-5 seconds.

**Why MMR retrieval instead of similarity search?**
Max Marginal Relevance avoids returning 4 nearly-identical chunks. It picks the most relevant AND most diverse chunks, giving the LLM better coverage of the knowledge base.

**Why temperature=0.2?**
Low temperature keeps the LLM grounded in the retrieved context. Higher temperature causes it to "fill in the gaps" with plausible-sounding but potentially incorrect information.

**Why save as draft instead of sending directly?**
Human-in-the-loop. The LLM is grounded but not infallible — a human review step before sending is the responsible default.

---
by Aman Pratap Singh



