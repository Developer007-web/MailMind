
# 📬 MailMind — AI Email Assistant

> **An intelligent Gmail assistant powered by RAG, MCP, and Groq that reads emails, retrieves relevant company knowledge, and drafts grounded replies with source citations.**

![Python](https://img.shields.io/badge/Python-3.10+-blue)
![LangChain](https://img.shields.io/badge/LangChain-RAG-green)
![Groq](https://img.shields.io/badge/Groq-Llama--3.3--70B-orange)
![FastAPI](https://img.shields.io/badge/FastAPI-API-success)
![Streamlit](https://img.shields.io/badge/Streamlit-UI-red)
![License](https://img.shields.io/badge/License-MIT-yellow)

---

## 🚀 Overview

**MailMind** is an AI-powered email assistant that connects directly to Gmail using the **Model Context Protocol (MCP)** and generates accurate, context-aware email drafts using **Retrieval-Augmented Generation (RAG)**.

Instead of relying solely on an LLM's internal knowledge, MailMind retrieves relevant information from your organization's documents before generating a response, significantly reducing hallucinations and improving factual accuracy.

Every generated response is saved as a **Gmail draft**, ensuring a **human-in-the-loop** workflow before emails are sent.

---

# ✨ Features

* 📥 Read unread Gmail messages
* 🤖 AI-generated email replies using Groq Llama 3.3 70B
* 📚 RAG-powered contextual retrieval
* 🔍 ChromaDB vector database
* 📄 Supports PDF, DOCX, TXT & Markdown knowledge bases
* ⚡ Fast generation using Groq inference
* 🧠 MMR retrieval for diverse context selection
* 📝 Save replies directly to Gmail Drafts
* 💻 Streamlit web interface
* 🔧 FastMCP Gmail integration
* 📊 Retrieval evaluation script
* 🔒 Human approval before sending

---

# 🏗️ Architecture

```text
                    Gmail Inbox
                         │
                         ▼
          MCP (Read Gmail Messages)
                         │
                         ▼
                  Email Content
                         │
                         ▼
          RAG Retrieval (ChromaDB)
                         │
      Top Relevant Company Documents
                         │
                         ▼
     Groq Llama-3.3-70B (Grounded Generation)
                         │
                         ▼
          Draft Response + Citations
                         │
                         ▼
          MCP (Save Gmail Draft)
                         │
                         ▼
              Gmail Drafts Folder
```

---

# 🛠️ Tech Stack

| Category          | Technology                    |
| ----------------- | ----------------------------- |
| LLM               | Groq Llama-3.3-70B            |
| Framework         | LangChain                     |
| Vector Database   | ChromaDB                      |
| Embeddings        | OpenAI text-embedding-3-small |
| Email Integration | Gmail API + FastMCP           |
| Backend           | FastAPI                       |
| Frontend          | Streamlit                     |
| Language          | Python                        |

---

# 📂 Project Structure

```text
MailMind/
│
├── app.py                 # Streamlit interface
├── agent.py               # CLI orchestrator
├── gmail_mcp.py           # MCP Gmail server
├── rag_chain.py           # RAG pipeline
├── ingest.py              # Document ingestion
├── eval.py                # Retrieval evaluation
├── requirements.txt
├── .env.example
│
├── company_docs/
│   ├── pdf/
│   ├── docx/
│   ├── txt/
│   └── md/
│
├── chroma_db/
│
├── credentials.json
└── token.json
```

---

# ⚙️ Installation

## 1. Clone Repository

```bash
git clone https://github.com/Developer007-web/MailMind.git

cd MailMind
```

---

## 2. Create Virtual Environment

```bash
python -m venv venv
```

### Windows

```bash
venv\Scripts\activate
```

### Linux / macOS

```bash
source venv/bin/activate
```

---

## 3. Install Dependencies

```bash
pip install -r requirements.txt
```

---

# 🔑 Environment Variables

Create a `.env` file.

| Variable         | Description              |
| ---------------- | ------------------------ |
| `GROQ_API_KEY`   | Groq API key             |
| `OPENAI_API_KEY` | OpenAI embedding API key |

---

# 📚 Add Knowledge Base

Place your company documents inside:

```text
company_docs/
```

Supported formats:

* PDF
* DOCX
* TXT
* Markdown

Generate embeddings:

```bash
python ingest.py
```

This creates a persistent ChromaDB vector store.

---

# 📧 Gmail OAuth Setup

1. Open Google Cloud Console.
2. Create a project.
3. Enable Gmail API.
4. Create an OAuth Desktop Application.
5. Download the credentials.
6. Rename the file to:

```text
credentials.json
```

7. Place it in the project root.
8. Run the project once to generate `token.json`.

---

# ▶️ Running the Project

## Streamlit UI

```bash
streamlit run app.py
```

---

## CLI Agent

Interactive mode

```bash
python agent.py
```

Auto-save drafts

```bash
python agent.py --auto --count 10
```

Process all emails

```bash
python agent.py --all
```

---

## Python API

```python
from rag_chain import draft_reply

result = draft_reply(
    "Can you clarify the refund policy for annual subscriptions?"
)

print(result["draft"])
print(result["sources"])
```

---

# 📈 Evaluation

Measure retrieval performance.

```bash
python eval.py
```

Example:

```text
Expected : refund-policy.pdf

Retrieved:
refund-policy.pdf
pricing.pdf

Precision@4 = 80%
```

---

# 🎯 Design Decisions

### Why Groq?

Groq provides extremely low-latency inference (~300 tokens/sec), making email generation nearly instantaneous while maintaining strong quality.

### Why Retrieval-Augmented Generation?

RAG grounds responses in your organization's documents instead of relying solely on model memory, reducing hallucinations and improving factual accuracy.

### Why MMR Retrieval?

Max Marginal Relevance returns relevant yet diverse document chunks, giving the model broader context and reducing redundant information.

### Why Save Drafts Instead of Sending Emails?

MailMind follows a **human-in-the-loop** workflow. Drafts are generated automatically but require user review before sending, ensuring greater reliability and safety.

---

# 🔮 Roadmap

* [ ] Multi-account Gmail support
* [ ] Outlook integration
* [ ] Slack integration
* [ ] Citation highlighting
* [ ] Web search fallback
* [ ] Conversation memory
* [ ] Fine-grained document permissions
* [ ] Docker deployment
* [ ] Kubernetes support

---

# 🤝 Contributing

Contributions are welcome!

1. Fork the repository.
2. Create a feature branch.
3. Commit your changes.
4. Open a Pull Request.

---

# 🔒 Security

* OAuth2 authentication for Gmail access
* API keys managed via environment variables
* Local ChromaDB vector storage
* Human approval before email sending
* No automatic outbound emails

---

# 📄 License

This project is licensed under the **MIT License**.

---

# 👨‍💻 Author

**Aman Pratap Singh**

* GitHub: **[https://github.com/Developer007-web](https://github.com/Developer007-web)**
* LinkedIn: **[https://linkedin.com/in/aman-pratap-singh](https://linkedin.com/in/aman-pratap-singh)**

---

⭐ **If you found this project useful, consider giving it a star! It helps others discover the project and supports future development.**

