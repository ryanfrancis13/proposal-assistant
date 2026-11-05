# Meridian Proposal Assistant

Generating enterprise sales proposals with an LLM is a classic high-stakes trap. If you hand a raw customer Request for Proposal (RFP) and a folder of company docs to a standard RAG pipeline, the model will happily miscalculate multi-year discounts, quote outdated prices from old case studies, promise cloud platforms your team doesn't actually support, or agree to delivery timelines that are physically impossible.

This repository is a research and engineering project built around a fictional cloud consultancy, **Meridian Cloudworks**. Instead of trusting an LLM to do math or police its own claims, the system splits proposal generation into four strict stages:

1. **Deterministic Commercial Pricing**: A rule-based pricing engine extracts scope facts (server counts, support duration, cloud accounts, requested discounts) and calculates the exact quote in Indian Rupees (`INR`) from official rate cards. The LLM never calculates a single number.
2. **Evidence-Grounded Section Drafting**: Requirements are broken down sentence by sentence, paired with relevant passages from Meridian's product specifications and past case studies via BM25 lexical search, and drafted with mandatory source citations (`[E1]`, `[E2]`, etc.).
3. **Deterministic Per-Section Verification (`V1`–`V7`)**: Every drafted section is audited by a deterministic verifier that checks citations, rejects outdated 2022 pricing sources, catches unsupported capabilities (like GCP, SAP HANA, mainframe, or HIPAA mappings), blocks unapproved currency figures or illegal discounts, and checks whether promised deadlines actually fit documented delivery timelines.
4. **Targeted Section Repair**: When a section fails verification, the pipeline doesn't throw away the whole document. It keeps every passing section and regenerates *only* the failed sections, passing the exact verifier error back to the model so it can fix the mistake in place.

---

## Why We Built This (The Research Question)

Alongside the working application, this repo powers an experimental study comparing three ways of handling compliance failures in LLM-generated proposals:

- **`none` (Single-Pass Baseline)**: Draft each section once and keep whatever the model outputs.
- **`whole_document` (Blind Resampling)**: If any section fails verification, regenerate the entire proposal once from scratch.
- **`targeted_section` (Targeted Repair)**: Regenerate only the sections that failed verification, injecting the exact policy violations (`V1`–`V7`) into the repair prompt.

### Summary of Benchmark Results

Tested across seven adversarial RFP trap categories (unsupported cloud platforms, discount cap violations, price floor breaches, unrealistic deadlines, unsupported certifications, out-of-scope workloads, and stale 2022 pricing references) using `nvidia/nemotron-3-ultra-550b-a55b` via NVIDIA NIM:

| Repair Strategy | Valid Runs (`V0` Timeouts) | Strict Compliance (95% CI) | Loose Compliance (95% CI) | Avg. Model Calls | Total Remaining Violations |
|---|---|---|---|---|---|
| **`none`** | 6 (1) | **0.0%** `[0.0%, 39.0%]` | **80.2%** `[73.6%, 86.7%]` | **3.00** | 44 (`V5: 25, V6: 12, V1: 5, V4: 2`) |
| **`whole_document`** | 5 (2) | **0.0%** `[0.0%, 43.4%]` | **81.0%** `[75.0%, 86.9%]` | **6.00** | 29 (`V6: 10, V5: 10, V1: 8, V4: 1`) |
| **`targeted_section`** | 5 (2) | **80.0%** `[37.6%, 96.4%]` | **99.0%** `[97.2%, 100.0%]` | **5.60** | **1** (`V3: 1`) |

*Note: `V0` denotes transient API timeouts on the hosted endpoint, which are tracked separately so network hiccups are never conflated with content compliance failures.*

---

## How the Pipeline Works Under the Hood

### 1. The Knowledge Base (`data/raw/`)
Meridian Cloudworks offers three core services documented in `data/raw/`:
- **Cloud Migration (`product_migration.md`)**: Fixed-scope AWS and Azure migrations (Discovery & Assessment, Landing Zone Build, Rehost at ₹38,000/server, Replatform at ₹1,15,000/workload, 12% Project Management, and 4 weeks of Hypercare). Explicitly excludes Google Cloud Platform (GCP), SAP HANA, and mainframe workloads.
- **Managed Cloud Support (`product_managed_support.md`)**: Post-migration monthly operations in Essential (₹2,400/server/mo), Standard (₹3,900/server/mo), and Premium 24x7x365 (₹6,200/server/mo) tiers. Requires at least 20 servers and a 12-month minimum term, with a 5% contractual discount on 24-month terms.
- **Cloud Security Posture Service (`product_security_addon.md`)**: Continuous CIS, ISO 27001, and RBI compliance drift scanning at ₹28,000/account/month (first 5 accounts) and ₹22,000/account/month beyond 5, with a 10% bundle discount when paired with Standard or Premium support. Explicitly excludes HIPAA control mappings.
- **Commercial Policy (`pricing_policy.md`)**: Defines discount ordering (contractual discounts first, negotiated discounts second), approval tiers, a strict **15% negotiated discount cap**, and an **80% overall price floor** relative to list price.
- **10 Historical Case Studies (`case_01_retail.md` – `case_10_govt.md`)**: Real-world delivery examples across retail, banking, healthcare, logistics, edtech, manufacturing, insurance, media, and SaaS. **Case 10 (`case_10_govt.md`)** intentionally contains superseded 2022 tender pricing and is flagged during ingestion so it can never be cited as current pricing evidence.

### 2. Commercial Rules (`R1`–`R7`) & Verifier Checks (`V1`–`V7`)

| Rule / Check | Layer | What It Enforces |
|---|---|---|
| **`R1` / `R2`** | Quote Engine | Managed support requires at least 20 servers (`R1`) and a 12-month minimum term (`R2`). |
| **`R3` / `R5`** | Quote Engine | Negotiated discounts cannot exceed 15% (`R3`), and total price after all discounts cannot fall below 80% of undiscounted list price (`R5`). |
| **`R4` / `R7`** | Quote Engine | CSPS 10% bundle discount requires Standard/Premium support (`R4`), and CSPS requires a 12-month minimum term (`R7`). |
| **`R6`** | Quote Engine | Soft flag noting management approval is required for negotiated discounts above 5%. |
| **`V1`** | Section Verifier | Every claim must cite supplied evidence IDs (`E1`–`E5`) and must never cite `superseded_pricing` (`case_10_govt.md`). |
| **`V2`** | Section Verifier | Blocks claims offering unsupported services (GCP, Google Cloud, SAP HANA, mainframe, HIPAA) unless explicitly declining them. |
| **`V3`** | Section Verifier | Blocks unapproved guarantee language (`"guarantee"`, `"guaranteed"`, `"will achieve"`, `"will reduce"`) unless used in a policy disclaimer. |
| **`V4`** | Section Verifier | Blocks any `INR` / `₹` currency figure not present in the validated deterministic quote, as well as promises of `>15%` discounts. |
| **`V5`** | Section Verifier | Requires every scope gap entry to begin with `"Not covered in our documents:"`. |
| **`V6`** | Section Verifier | Enforces status consistency (`answered` sections cannot list gaps; `no_evidence` sections cannot list claims). |
| **`V7`** | Section Verifier | Blocks claims stating a deadline is achievable when the customer's timeline is shorter than the documented minimum for their server count. |

---

## Project Structure

```text
proposal-assistant/
├── config/
│   └── settings.yaml                 # Active NIM generator/embedding models & retrieval top-k
├── data/
│   ├── eval/                         # Sample customer RFPs (retail & healthcare)
│   └── raw/                          # Product specs, pricing policy, and 10 case studies
├── src/proposal_assistant/
│   ├── cli.py                        # Command-line RFP-to-DOCX generator
│   ├── config.py                     # Settings & .env credential loader
│   ├── experiment_cli.py             # CLI runner for synthetic repair experiments
│   ├── experiments.py                # Trial runner, Wilson/normal CIs, and V0 separation
│   ├── export.py                     # Word (.docx) proposal formatter
│   ├── extraction.py                 # Requirement splitter & quote fact extractor
│   ├── generation.py                 # NVIDIA NIM client, prompt builder & JSON schema parser
│   ├── ingestion.py                  # Markdown section chunker & stale-source tagger
│   ├── models.py                     # Typed dataclasses and enums across the pipeline
│   ├── pipeline.py                   # End-to-end orchestration (extract -> quote -> retrieve -> verify)
│   ├── pricing.py                    # Rate-card calculator, INR formatter & R1-R7 validator
│   ├── quote_builder.py              # Quote builder with explicit assumption tracking
│   ├── repair.py                     # Implementation of none, whole_document & targeted_section
│   ├── retrieval.py                  # Heading-aware BM25 lexical evidence retriever
│   ├── synthetic.py                  # Reproducible generator for the 7 adversarial RFP traps
│   ├── verification.py               # Deterministic V1-V7 section verifier
│   └── web.py                        # Built-in Light/Dark web UI & JSON API server
├── tests/                            # 56 offline pytest unit tests covering every module
├── .env.example                      # Template for NVIDIA NIM API keys
├── pyproject.toml                    # Package metadata & pytest configuration
└── requirements.txt                  # Python dependencies
```

---

## Getting Started

### 1. Install Dependencies
Make sure you have Python 3.10+ installed, then create and activate a virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install -e .
```

### 2. Configure Your NVIDIA NIM API Keys
Copy `.env.example` to `.env` in the project root and paste your key from [build.nvidia.com](https://build.nvidia.com):

```env
NVIDIA_GENERATOR_KEY=nvapi-your-key-here
NVIDIA_EMBEDDING_KEY=nvapi-your-key-here
NIM_BASE_URL=https://integrate.api.nvidia.com/v1
```

*(Don't have an API key handy? The web app also includes an **Instant Offline Preview** mode so you can test the quote calculator, verifier, and Word export without making live API calls.)*

---

## Running the Project

### Option A: Interactive Web UI (Recommended)
Launch the local web server:

```powershell
python -m proposal_assistant.web
```

Then open **http://127.0.0.1:8000** in your browser. From the web dashboard you can:
- Load sample customer RFPs or paste your own custom RFP text.
- Switch between **Targeted Section Repair**, **Rewrite Entire Draft**, or **Single Draft Pass**.
- Inspect the itemized INR quote, commercial assumptions, policy notes, and requirement-by-requirement responses with expandable source citations.
- Download the formatted **Word Document (`proposal.docx`)** with one click.

### Option B: Command-Line Proposal Generator
Generate a `.docx` proposal directly from any text file:

```powershell
python -m proposal_assistant.cli data\eval\sample_rfp_01.txt --output proposal.docx
```

You can also specify `--condition none`, `--condition whole_document`, or `--condition targeted_section` (the default).

### Option C: Running the Synthetic Repair Experiment
To reproduce the experimental comparison across the 7 trap categories:

```powershell
python -m proposal_assistant.experiment_cli --count 7 --repeats 1 --seed 7 --output results --timeout 90
```

This writes per-trial records to `results/records.json` and aggregated compliance metrics with 95% confidence intervals to `results/summary.json` and `results/summary.csv`.

### Running the Offline Test Suite
All 56 unit tests run completely offline in ~5 seconds using deterministic test doubles:

```powershell
python -m pytest -q
```
