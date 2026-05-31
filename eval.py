"""
eval.py
-------
Retrieval evaluation: measures precision@k on a test set.
Run after ingesting docs to verify your RAG pipeline quality.

Usage:
    python eval.py
"""

import os
from dotenv import load_dotenv
from rag_chain import retrieve_only

load_dotenv()

# ─────────────────────────────────────────────
# TEST SET — edit these to match your actual docs
# Each entry: { "query": ..., "expected_sources": [...] }
# expected_sources = list of filenames that SHOULD appear in top-k
# ─────────────────────────────────────────────
TEST_CASES = [
    {
        "query": "What is the refund policy for annual subscriptions?",
        "expected_sources": ["refund-policy.pdf", "pricing.pdf"],
    },
    {
        "query": "How many days of paid leave do employees get?",
        "expected_sources": ["hr-policy.pdf", "employee-handbook.pdf"],
    },
    {
        "query": "What are the enterprise pricing tiers?",
        "expected_sources": ["pricing.pdf"],
    },
    {
        "query": "How do I reset my password?",
        "expected_sources": ["support-guide.pdf", "faq.txt"],
    },
    {
        "query": "What is the SLA for support tickets?",
        "expected_sources": ["support-guide.pdf", "sla.pdf"],
    },
]

K = 4  # top-k chunks to retrieve


def evaluate():
    print("═" * 60)
    print("  RAG Retrieval Evaluation  |  precision@k")
    print("═" * 60)
    print(f"  K = {K}  |  {len(TEST_CASES)} test cases\n")

    hits = 0
    total = 0

    for i, tc in enumerate(TEST_CASES, 1):
        query = tc["query"]
        expected = set(tc["expected_sources"])

        results = retrieve_only(query, k=K)
        retrieved_sources = {r["source"] for r in results}

        matched = expected & retrieved_sources
        hit = len(matched) > 0

        if hit:
            hits += 1
        total += 1

        status = "✓" if hit else "✗"
        print(f"  [{status}] {query[:55]}...")
        print(f"       Expected : {', '.join(expected)}")
        print(f"       Retrieved: {', '.join(retrieved_sources)}")
        if results:
            top_score = results[0]["score"]
            print(f"       Top score: {top_score:.4f}")
        print()

    precision = hits / total if total > 0 else 0
    print("─" * 60)
    print(f"  Precision@{K}: {hits}/{total} = {precision:.1%}")

    if precision >= 0.8:
        print("  ✓ Good retrieval quality (≥80%)")
    elif precision >= 0.6:
        print("  ~ Acceptable retrieval (≥60%) — consider tuning chunk size")
    else:
        print("  ✗ Poor retrieval (<60%) — review chunking strategy and docs")

    print("═" * 60)
    return precision


if __name__ == "__main__":
    evaluate()
