from openai import OpenAI

from proposal_assistant.config import api_key, base_url


def main():
    client = OpenAI(api_key=api_key(), base_url=base_url())
    models = sorted(m.id for m in client.models.list().data)
    print(f"{len(models)} models available\n")
    for name in models:
        print(name)


if __name__ == "__main__":
    main()