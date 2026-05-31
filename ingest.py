"""
ingest.py
---------
Load company documents → chunk → embed → persist to ChromaDB.
Run this once (or whenever you add/update docs):
    python ingest.py
"""

import os
import sys
from dotenv import load_dotenv
from langchain_community.document_loaders import DirectoryLoader, PyPDFLoader
from langchain_community.document_loaders import Docx2txtLoader, TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma

load_dotenv()

DOCS_DIR = os.getenv("DOCS_DIR", "./company_docs")
CHROMA_DIR = os.getenv("CHROMA_DIR", "./chroma_db")


def load_documents():
    """Load PDF, DOCX, TXT, and MD files from DOCS_DIR."""
    docs = []

    # PDF loader
    pdf_loader = DirectoryLoader(
        DOCS_DIR,
        glob="**/*.pdf",
        loader_cls=PyPDFLoader,
        show_progress=True,
        use_multithreading=True,
    )
    # DOCX loader
    docx_loader = DirectoryLoader(
        DOCS_DIR,
        glob="**/*.docx",
        loader_cls=Docx2txtLoader,
        show_progress=True,
    )
    # TXT / MD loader
    txt_loader = DirectoryLoader(
        DOCS_DIR,
        glob="**/*.txt",
        loader_cls=TextLoader,
        show_progress=True,
        loader_kwargs={"autodetect_encoding": True},
    )

    for loader in [pdf_loader, docx_loader, txt_loader]:
        try:
            loaded = loader.load()
            docs.extend(loaded)
        except Exception as e:
            print(f"Warning loading {loader.__class__.__name__}: {e}")

    return docs


def chunk_documents(docs):
    """Split documents into overlapping chunks."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50,
        separators=["\n\n", "\n", ". ", " ", ""],
        length_function=len,
    )
    chunks = splitter.split_documents(docs)
    return chunks


def embed_and_store(chunks):
    """Embed chunks and persist to ChromaDB using free local HuggingFace embeddings."""
    embeddings = HuggingFaceEmbeddings(
        model_name="all-MiniLM-L6-v2",
        model_kwargs={"device": "cpu"},
    )
    vectorstore = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory=CHROMA_DIR,
        collection_name="company_docs",
    )
    return vectorstore


def main():
    print(f"Loading documents from: {DOCS_DIR}")

    if not os.path.exists(DOCS_DIR):
        os.makedirs(DOCS_DIR)
        print(f"Created {DOCS_DIR}/ — add your company docs (PDF/DOCX/TXT) and run again.")
        sys.exit(0)

    docs = load_documents()
    if not docs:
        print("No documents found. Add files to company_docs/ and run again.")
        sys.exit(0)

    print(f"Loaded {len(docs)} documents.")

    chunks = chunk_documents(docs)
    print(f"Created {len(chunks)} chunks.")

    print("Embedding and storing in ChromaDB...")
    vectorstore = embed_and_store(chunks)
    print(f"Done. {len(chunks)} chunks stored in {CHROMA_DIR}/")

    # Quick sanity check
    results = vectorstore.similarity_search("test query", k=2)
    print(f"Sanity check passed — retrieved {len(results)} chunks for test query.")


if __name__ == "__main__":
    main()