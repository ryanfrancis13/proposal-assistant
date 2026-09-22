from openai import OpenAI

from proposal_assistant.config import base_url, embedding_key, generator_key, load_settings


def main():
    models = load_settings()["models"]
    url = base_url()

    gen_client = OpenAI(api_key=generator_key(), base_url=url, timeout=30.0)
    emb_client = OpenAI(api_key=embedding_key(), base_url=url, timeout=30.0)

    print(f"testing generator: {models['generator']}")
    try:
        reply = gen_client.chat.completions.create(
            model=models["generator"],
            messages=[{"role": "user", "content": "Reply with the single word: ready"}],
            max_tokens=10,
        )
        print("  OK ->", reply.choices[0].message.content.strip())
    except Exception as e:
        print("  FAIL ->", type(e).__name__, str(e)[:200])

    print(f"testing embedding: {models['embedding']}")
    try:
        emb = emb_client.embeddings.create(
            model=models["embedding"],
            input=["cloud migration"],
            extra_body={"input_type": "query", "truncate": "END"},
        )
        print("  OK -> dims:", len(emb.data[0].embedding))
    except Exception as e:
        print("  FAIL ->", type(e).__name__, str(e)[:200])


if __name__ == "__main__":
    main()