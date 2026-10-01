DRAFT_PROMPT = """You are drafting one section of a sales proposal for Meridian \
Cloudworks, an IT services company offering cloud migration and managed cloud \
support.

The customer has this requirement:
Topic: {topic}
Detail: {detail}

Here is evidence from Meridian's own product documentation and past case studies. \
Use ONLY the facts in this evidence. If the evidence does not support a confident \
answer, say so plainly rather than guessing.

Evidence:
{evidence_text}

Write a short paragraph (3-5 sentences) addressing the customer's requirement, \
written in a professional proposal tone. Do not invent prices, dates, or \
capabilities not shown in the evidence above.
"""


def draft_section(requirement: dict, generator_model: str, client) -> str:
    evidence_text = "\n\n".join(
        f"[{e['source_file']}] {e['text']}" for e in requirement["evidence"]
    )
    prompt = DRAFT_PROMPT.format(
        topic=requirement["topic"],
        detail=requirement["detail"],
        evidence_text=evidence_text,
    )
    response = client.chat.completions.create(
        model=generator_model,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=300,
    )
    return response.choices[0].message.content.strip()


PRICING_NARRATION_PROMPT = """You are writing the pricing section of a proposal for \
Meridian Cloudworks. Below are the EXACT computed figures from our pricing engine. \
Do not alter, recalculate, or round these numbers. Present them clearly in \
professional proposal language. If any assumptions are listed, state them plainly \
so the customer knows to confirm or correct them.

Computed figures:
{figures_text}

Assumptions made (state these explicitly in the section):
{assumptions_text}

Rule violations (if any must be flagged to the customer):
{violations_text}

Write a short pricing section (4-6 sentences).
"""


def draft_pricing_section(quote, assumptions: list[str], client, model: str) -> str:
    figures_text = (
        f"Migration subtotal: INR {quote.migration_subtotal():,.2f}\n"
        f"Support subtotal: INR {quote.support_subtotal():,.2f}\n"
        f"Total: INR {quote.subtotal():,.2f}"
    )
    assumptions_text = "\n".join(f"- {a}" for a in assumptions) or "None"
    violations_text = (
        "\n".join(f"- {v[2]}" for v in quote.violations) if quote.violations else "None"
    )

    prompt = PRICING_NARRATION_PROMPT.format(
        figures_text=figures_text,
        assumptions_text=assumptions_text,
        violations_text=violations_text,
    )
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=350,
    )
    return response.choices[0].message.content.strip()