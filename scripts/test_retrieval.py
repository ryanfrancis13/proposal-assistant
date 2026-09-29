from proposal_assistant.retrieval import HybridRetriever

QUERIES = [
    "Can you migrate SAP HANA workloads?",
    "What is your response time for a critical incident?",
    "Do you have experience with hospital or healthcare data?",
    "What discount applies for a 24 month support contract?",
]


def main():
    retriever = HybridRetriever()
    for q in QUERIES:
        print(f"\nQuery: {q}")
        for r in retriever.search(q, top_k=5):
            preview = r["text"][:100].replace("\n", " ")
            print(f"  [{r['score']:.3f}] {r['source_file']} :: {preview}...")


if __name__ == "__main__":
    main()