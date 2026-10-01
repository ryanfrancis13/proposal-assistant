import json

from openai import OpenAI

from proposal_assistant.config import base_url, load_settings, generator_key

from proposal_assistant.retrieval import HybridRetriever

EXTRACTION_PROMPT = """You are reading a customer's RFP (request for proposal) for an IT \
services company called Meridian Cloudworks, which provides cloud migration and \
managed cloud support services.

Extract the customer's requirements as a JSON array. Each item must have:
- "topic": a short label (e.g. "server count", "cloud provider", "compliance")
- "detail": the specific requirement, in your own words, one sentence

Only include things the RFP actually states or asks about. Do not invent requirements.
Return ONLY the JSON array, nothing else — no markdown fences, no commentary.

RFP text:
{rfp_text}
"""


def extract_requirements(rfp_text: str) -> list[dict]:
    settings = load_settings()
    client = OpenAI(api_key=generator_key(), base_url=base_url(), timeout=60.0)

    response = client.chat.completions.create(
        model=settings["models"]["generator"],
        messages=[{"role": "user", "content": EXTRACTION_PROMPT.format(rfp_text=rfp_text)}],
        max_tokens=800,
    )

    raw = response.choices[0].message.content.strip()
    return json.loads(raw)


def gather_evidence(requirements: list[dict], retriever: HybridRetriever, top_k: int = 5) -> list[dict]:
    enriched = []
    for req in requirements:
        query = f"{req['topic']}: {req['detail']}"
        hits = retriever.search(query, top_k=top_k)
        enriched.append({**req, "evidence": hits})
    return enriched


QUOTE_INPUT_PROMPT = """From this RFP text, extract pricing-relevant facts as JSON. \
Use null for anything not stated — do not guess or infer missing values.

Fields:
- "server_count": integer or null
- "rehost_servers": integer or null (if not split out, use null)
- "replatform_workloads": integer or null
- "clouds": integer or null (1 for single cloud, 2+ for multi-cloud)
- "wants_support": true, false, or null if not mentioned
- "support_term_months": integer or null

Return ONLY the JSON object, nothing else.

RFP text:
{rfp_text}
"""


def extract_quote_inputs(rfp_text: str, client, model: str) -> dict:
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": QUOTE_INPUT_PROMPT.format(rfp_text=rfp_text)}],
        max_tokens=200,
    )
    raw = response.choices[0].message.content.strip()
    return json.loads(raw)