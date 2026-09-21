from openai import OpenAI

from proposal_assistant.config import api_key, base_url, load_settings


def main():
    client = OpenAI(api_key=api_key(), base_url=base_url())
    models = load_settings()["models"]

    reply = client.chat.completions.create(
        model=models["generator"],
        messages=[{"role": "user", "content": "Reply with the single word: ready"}],
        max_tokens=10,
    )
    print("generator:", reply.choices[0].message.content.strip())

    emb = client.embeddings.create(
        model=models["embedding"],
        input=["cloud migration"],
        extra_body={"input_type": "query", "truncate": "END"},
    )
    print("embedding dims:", len(emb.data[0].embedding))


if __name__ == "__main__":
    main()