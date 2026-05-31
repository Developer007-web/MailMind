"""
rag_chain.py
------------
Retrieval-Augmented Generation chain using:
- ChromaDB as vector store
- HuggingFace all-MiniLM-L6-v2 for embeddings (free, local)
- Groq (llama-3.3-70b-versatile) as the LLM

Usage:
    from rag_chain import draft_reply
    result = draft_reply("Can you clarify your refund policy?")
    print(result["draft"])
    print(result["sources"])
"""

import os
from functools import lru_cache
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate

load_dotenv()

EMAIL_DRAFT_PROMPT = PromptTemplate(
    input_variables=["context", "question"],
    template="""You are a professional email assistant for a company.
Your task is to draft a clear, concise, and polite email reply.

RULES:
1. Use ONLY the information provided in the context below.
2. If the context does not contain enough information, write:
   "I don't have enough information in our knowledge base to answer this accurately.
    I'll follow up after checking with the relevant team."
3. Keep the reply professional and under 150 words.
4. Do NOT invent policies, prices, or procedures not found in the context.
5. End with a helpful closing line.

--- COMPANY KNOWLEDGE BASE CONTEXT ---
{context}
--- END CONTEXT ---

Email received:
{question}

Draft reply:""",
)


@lru_cache(maxsize=1)
def _get_chain():
    """Build and cache the RAG chain (expensive to rebuild)."""
    embeddings = HuggingFaceEmbeddings(
        model_name="all-MiniLM-L6-v2",
        model_kwargs={"device": "cpu"},
    )
    vectorstore = Chroma(
        persist_directory=os.getenv("CHROMA_DIR", "./chroma_db"),
        embedding_function=embeddings,
        collection_name="company_docs",
    )
    retriever = vectorstore.as_retriever(
        search_type="mmr",  # Max Marginal Relevance — avoids redundant chunks
        search_kwargs={
            "k": int(os.getenv("RETRIEVAL_K", "4")),
            "fetch_k": 20,  # fetch 20, then pick best 4 via MMR
        },
    )
    llm = ChatGroq(
        model=os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
        temperature=0.2,  # Low temperature = more grounded, less hallucination
        max_tokens=512,
        api_key=os.getenv("GROQ_API_KEY"),
    )
    chain = RetrievalQA.from_chain_type(
        llm=llm,
        chain_type="stuff",
        retriever=retriever,
        return_source_documents=True,
        chain_type_kwargs={"prompt": EMAIL_DRAFT_PROMPT},
    )
    return chain


def draft_reply(email_body: str) -> dict:
    """
    Generate a grounded email draft from a given email body.

    Args:
        email_body: The text content of the email to reply to.

    Returns:
        {
            "draft": str,       # The generated reply
            "sources": list,    # Source document filenames used
            "chunks": list,     # Raw retrieved chunks (for debugging)
        }
    """
    chain = _get_chain()
    result = chain.invoke({"query": email_body})

    sources = list({
        os.path.basename(doc.metadata.get("source", "unknown"))
        for doc in result["source_documents"]
    })
    chunks = [
        {
            "source": os.path.basename(doc.metadata.get("source", "unknown")),
            "page": doc.metadata.get("page", "N/A"),
            "content": doc.page_content[:200] + "..." if len(doc.page_content) > 200 else doc.page_content,
        }
        for doc in result["source_documents"]
    ]

    return {
        "draft": result["result"].strip(),
        "sources": sources,
        "chunks": chunks,
    }


def retrieve_only(query: str, k: int = 4) -> list:
    """
    Debug helper: retrieve chunks without generating a reply.
    """
    embeddings = HuggingFaceEmbeddings(
        model_name="all-MiniLM-L6-v2",
        model_kwargs={"device": "cpu"},
    )
    vectorstore = Chroma(
        persist_directory=os.getenv("CHROMA_DIR", "./chroma_db"),
        embedding_function=embeddings,
        collection_name="company_docs",
    )
    docs = vectorstore.similarity_search_with_relevance_scores(query, k=k)
    return [
        {
            "source": os.path.basename(doc.metadata.get("source", "unknown")),
            "score": round(score, 4),
            "content": doc.page_content,
        }
        for doc, score in docs
    ]


if __name__ == "__main__":
    # Quick test
    test_email = "Hi, could you explain what your refund policy is for annual subscriptions?"
    print("Testing RAG chain...")
    result = draft_reply(test_email)
    print("\n--- DRAFT ---")
    print(result["draft"])
    print("\n--- SOURCES ---")
    print(result["sources"])
    print("\n--- CHUNKS USED ---")
    for c in result["chunks"]:
        print(f"  [{c['source']} p.{c['page']}] {c['content']}")