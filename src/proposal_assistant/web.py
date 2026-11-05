import argparse
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import re
from typing import Any

from proposal_assistant.config import ROOT, Settings, load_settings
from proposal_assistant.export import export_docx
from proposal_assistant.generation import NIMGenerator
from proposal_assistant.models import RepairCondition, as_jsonable
from proposal_assistant.pipeline import PipelineResult, run_pipeline
from proposal_assistant.pricing import format_inr


SAMPLE_METADATA = {
    "sample_rfp_01": "Retail Infrastructure Migration & Managed Support (40 Servers)",
    "sample_rfp_02": "Healthcare Cloud Migration & Compliance Inquiry (35 Servers)",
}

STATUS_LABELS = {
    "answered": "Fully Supported",
    "partial": "Partially Supported",
    "cannot_fulfil": "Outside Current Scope",
    "no_evidence": "Requires Custom Scoping",
}

TOPIC_LABELS = {
    "estate size": "Infrastructure Scope",
    "timeline": "Delivery Timeline",
    "managed support": "Managed Cloud Support",
    "security and compliance": "Security & Compliance",
    "commercials": "Commercials & Pricing",
    "platform": "Target Cloud Platform",
    "general requirement": "General Requirement",
}


class DemoGenerator:
    """Offline deterministic generator that drafts valid cited sections from evidence."""

    def __init__(self) -> None:
        self.calls = 0

    def generate(self, prompt: str) -> str:
        self.calls += 1
        req_match = re.search(r"Requirement:\s*(.+)", prompt)
        requirement = (req_match.group(1).strip() if req_match else "").lower()
        evidence_ids = re.findall(r"\[(E\d+)\]\s+([^\n>]+)", prompt)
        current_id = "E1"
        for eid, source_file in evidence_ids:
            if "case_10_govt.md" not in source_file:
                current_id = eid
                break

        unsupported = [
            label
            for token, label in (
                ("google cloud", "Google Cloud Platform migration"),
                ("gcp", "GCP migration"),
                ("sap hana", "SAP HANA workload migration"),
                ("mainframe", "mainframe migration"),
                ("hipaa", "HIPAA control mappings"),
            )
            if token in requirement
        ]
        if unsupported:
            return json.dumps(
                {
                    "status": "cannot_fulfil",
                    "claims": [
                        {
                            "text": (
                                "Meridian Cloudworks supports AWS and Microsoft Azure and "
                                f"does not offer {', '.join(unsupported)}."
                            ),
                            "evidence": [current_id],
                        }
                    ],
                    "gaps": [
                        f"Not covered in our documents: {', '.join(unsupported)}"
                    ],
                }
            )
        if "20%" in requirement or "20 percent" in requirement:
            return json.dumps(
                {
                    "status": "cannot_fulfil",
                    "claims": [
                        {
                            "text": (
                                "Meridian cannot offer a 20% discount because negotiated "
                                "discounts above 15% are not permitted under the commercial policy."
                            ),
                            "evidence": [current_id],
                        }
                    ],
                    "gaps": [
                        "Not covered in our documents: negotiated discounts above the 15% cap"
                    ],
                }
            )
        return json.dumps(
            {
                "status": "answered",
                "claims": [
                    {
                        "text": (
                            "Meridian Cloudworks delivers fixed-scope AWS and Azure migration, "
                            "managed cloud support, and security posture services under the current rate card."
                        ),
                        "evidence": [current_id],
                    }
                ],
                "gaps": [],
            }
        )


def _clean_rfp_paragraphs(raw_text: str) -> str:
    """Reflow hard-wrapped lines into clean readable paragraphs."""
    paragraphs = re.split(r"\n\s*\n", raw_text.strip())
    return "\n\n".join(
        " ".join(line.strip() for line in para.splitlines() if line.strip())
        for para in paragraphs
        if para.strip()
    )


def build_presets(root: Path = ROOT) -> dict[str, Any]:
    eval_dir = root / "data" / "eval"
    presets: list[dict[str, str]] = []
    if eval_dir.exists():
        for path in sorted(eval_dir.glob("*.txt")):
            presets.append(
                {
                    "id": path.stem,
                    "label": SAMPLE_METADATA.get(
                        path.stem, path.stem.replace("_", " ").title()
                    ),
                    "text": _clean_rfp_paragraphs(path.read_text(encoding="utf-8")),
                }
            )
    return {"presets": presets}


def serialize_pipeline_result(
    result: PipelineResult,
    llm_calls: int,
    condition: RepairCondition,
    mode: str,
) -> dict[str, Any]:
    quote = result.quote
    initial_by_id = {
        item.requirement_id: item for item in result.repair.initial_verifications
    }
    final_by_id = {
        item.requirement_id: item for item in result.repair.verifications
    }
    req_by_id = {item.requirement_id: item for item in result.requirements}

    sections_payload = []
    for index, section in enumerate(result.repair.draft.sections, start=1):
        req = req_by_id.get(section.requirement_id)
        initial_v = initial_by_id.get(section.requirement_id)
        final_v = final_by_id.get(section.requirement_id)
        raw_topic = req.topic if req else "general requirement"
        sections_payload.append(
            {
                "requirement_id": section.requirement_id,
                "display_number": index,
                "topic": TOPIC_LABELS.get(raw_topic, raw_topic.title()),
                "detail": req.detail if req else "",
                "status": section.status.value,
                "status_label": STATUS_LABELS.get(
                    section.status.value, section.status.value.replace("_", " ").title()
                ),
                "claims": as_jsonable(section.claims),
                "gaps": list(section.gaps),
                "initial_passed": bool(initial_v.passed) if initial_v else True,
                "initial_issues": as_jsonable(initial_v.issues) if initial_v else [],
                "final_passed": bool(final_v.passed) if final_v else True,
                "final_issues": as_jsonable(final_v.issues) if final_v else [],
                "evidence": as_jsonable(
                    result.evidence_by_requirement.get(section.requirement_id, [])
                ),
            }
        )

    passed_count = sum(1 for item in result.repair.verifications if item.passed)
    total_count = len(result.repair.verifications)
    return {
        "condition": condition.value,
        "mode": mode,
        "llm_calls": llm_calls,
        "verified_sections": passed_count,
        "total_sections": total_count,
        "strict_compliance": passed_count == total_count and total_count > 0,
        "quote_inputs": as_jsonable(result.quote_inputs),
        "quote": {
            "migration_subtotal": f"INR {format_inr(quote.migration_subtotal())}",
            "support_subtotal": f"INR {format_inr(quote.support_subtotal())}",
            "csps_subtotal": f"INR {format_inr(quote.csps_subtotal())}",
            "subtotal": f"INR {format_inr(quote.subtotal())}",
            "negotiated_discount": f"INR {format_inr(quote.negotiated_discount_amount())}",
            "total": f"INR {format_inr(quote.total())}",
            "violations": as_jsonable(quote.violations),
        },
        "assumptions": result.assumptions,
        "sections": sections_payload,
    }


def execute_proposal_request(
    rfp_text: str,
    condition_str: str = "targeted_section",
    mode: str = "nim",
    root: Path = ROOT,
    settings: Settings | None = None,
    docx_path: Path | None = None,
) -> dict[str, Any]:
    if not rfp_text or not rfp_text.strip():
        raise ValueError("RFP text must not be empty.")
    settings = settings or load_settings()
    condition = RepairCondition(condition_str)
    generator = (
        DemoGenerator()
        if mode == "demo"
        else NIMGenerator(settings.generator_model, timeout=90.0)
    )
    result = run_pipeline(
        rfp_text.strip(),
        generator,
        root / "data" / "raw",
        settings=settings,
        condition=condition,
    )
    output_docx = docx_path or (root / "proposal.docx")
    export_docx(
        output_docx,
        result.repair.draft,
        result.quote,
        result.assumptions,
        result.requirements,
    )
    return serialize_pipeline_result(
        result,
        llm_calls=int(getattr(generator, "calls", 0)),
        condition=condition,
        mode=mode,
    )


INDEX_HTML = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="color-scheme" content="light dark">
  <script>
    try {
      document.querySelector('meta[name="color-scheme"]').content =
        localStorage.getItem("color-scheme") ?? "light dark";
    } catch (e) {}
  </script>
  <title>Meridian Cloudworks — Proposal Assistant</title>
  <style>
    :root {
      color-scheme: light dark;

      &:has(> head > meta[name="color-scheme"][content="dark"]) {
        color-scheme: dark;
      }
      &:has(> head > meta[name="color-scheme"][content="light"]) {
        color-scheme: light;
      }

      --bg-light: #f8fafc;
      --bg-dark: #09090b;
      --surface-light: #ffffff;
      --surface-dark: #121215;
      --surface-muted-light: #f1f5f9;
      --surface-muted-dark: #1b1b20;
      --border-light: #e2e8f0;
      --border-dark: #27272a;
      --text-light: #0f172a;
      --text-dark: #f4f4f5;
      --muted-light: #475569;
      --muted-dark: #a1a1aa;
      --primary-bg-light: #18181b;
      --primary-bg-dark: #f4f4f5;
      --primary-fg-light: #ffffff;
      --primary-fg-dark: #09090b;

      --bg: var(--bg-light);
      --surface: var(--surface-light);
      --surface-muted: var(--surface-muted-light);
      --border: var(--border-light);
      --text: var(--text-light);
      --muted: var(--muted-light);
      --primary-bg: var(--primary-bg-light);
      --primary-fg: var(--primary-fg-light);

      @media (prefers-color-scheme: dark) {
        --bg: var(--bg-dark);
        --surface: var(--surface-dark);
        --surface-muted: var(--surface-muted-dark);
        --border: var(--border-dark);
        --text: var(--text-dark);
        --muted: var(--muted-dark);
        --primary-bg: var(--primary-bg-dark);
        --primary-fg: var(--primary-fg-dark);
      }

      @supports (color: light-dark(white, black)) {
        --bg: light-dark(var(--bg-light), var(--bg-dark));
        --surface: light-dark(var(--surface-light), var(--surface-dark));
        --surface-muted: light-dark(var(--surface-muted-light), var(--surface-muted-dark));
        --border: light-dark(var(--border-light), var(--border-dark));
        --text: light-dark(var(--text-light), var(--text-dark));
        --muted: light-dark(var(--muted-light), var(--muted-dark));
        --primary-bg: light-dark(var(--primary-bg-light), var(--primary-bg-dark));
        --primary-fg: light-dark(var(--primary-fg-light), var(--primary-fg-dark));
      }

      --ok: light-dark(#15803d, #4ade80);
      --ok-bg: light-dark(#dcfce7, rgba(34, 197, 94, 0.14));
      --warn: light-dark(#b45309, #fbbf24);
      --warn-bg: light-dark(#fef3c7, rgba(245, 158, 11, 0.15));
      --err: light-dark(#be123c, #fb7185);
      --err-bg: light-dark(#ffe4e6, rgba(244, 63, 94, 0.15));
      --radius: 10px;
    }

    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: Inter, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      background: var(--bg);
      color: var(--text);
      line-height: 1.55;
      min-block-size: 100vh;
    }
    header {
      border-block-end: 1px solid var(--border);
      background: var(--surface);
      padding: 1.1rem 2rem;
    }
    .header-inner {
      max-inline-size: 1240px;
      margin: 0 auto;
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      justify-content: space-between;
      gap: 1rem;
    }
    header h1 {
      margin: 0;
      font-size: 1.25rem;
      font-weight: 700;
      letter-spacing: -0.02em;
    }
    header p {
      margin: 0.15rem 0 0;
      color: var(--muted);
      font-size: 0.88rem;
    }
    main {
      max-inline-size: 1240px;
      margin: 0 auto;
      padding: 1.5rem 2rem 3rem;
      display: grid;
      gap: 1.5rem;
    }
    .steps-bar {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
      gap: 1rem;
    }
    .step-item {
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: var(--radius);
      padding: 1rem 1.15rem;
    }
    .step-num {
      font-size: 0.75rem;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.06em;
      color: var(--muted);
    }
    .step-title {
      font-weight: 600;
      font-size: 0.95rem;
      margin: 0.2rem 0;
    }
    .step-desc {
      font-size: 0.84rem;
      color: var(--muted);
      margin: 0;
    }
    .grid-2 {
      display: grid;
      grid-template-columns: minmax(340px, 1fr) minmax(380px, 1.35fr);
      gap: 1.5rem;
      align-items: start;
    }
    @media (max-width: 920px) {
      .grid-2 { grid-template-columns: 1fr; }
    }
    .card {
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: var(--radius);
      padding: 1.4rem;
    }
    .card h2 {
      margin: 0 0 1rem;
      font-size: 1.05rem;
      font-weight: 600;
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      justify-content: space-between;
      gap: 0.5rem;
    }
    label {
      display: block;
      font-size: 0.84rem;
      font-weight: 600;
      margin-block-end: 0.35rem;
    }
    .field-hint {
      font-size: 0.8rem;
      color: var(--muted);
      margin: 0.3rem 0 0;
    }
    .form-row {
      display: grid;
      gap: 1.1rem;
    }
    .controls-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 0.85rem;
    }
    @media (max-width: 540px) {
      .controls-grid { grid-template-columns: 1fr; }
    }
    .actions-row {
      display: flex;
      flex-wrap: wrap;
      gap: 0.75rem;
      align-items: center;
      margin-block-start: 0.25rem;
    }
    select, input {
      background: var(--surface-muted);
      color: var(--text);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 0.55rem 0.75rem;
      font: inherit;
      font-size: 0.9rem;
      width: 100%;
    }
    textarea {
      background: var(--surface-muted);
      color: var(--text);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 0.8rem;
      font: inherit;
      font-size: 0.92rem;
      field-sizing: content;
      height: auto;
      width: 100%;
      min-block-size: 7lh;
      max-block-size: 16lh;
      resize: vertical;
    }
    button {
      cursor: pointer;
      border-radius: 8px;
      padding: 0.6rem 1.1rem;
      font: inherit;
      font-size: 0.9rem;
      font-weight: 600;
      transition: opacity 0.15s ease;
    }
    button:disabled {
      opacity: 0.5;
      cursor: not-allowed;
    }
    .btn-primary {
      background: var(--primary-bg);
      color: var(--primary-fg);
      border: 1px solid var(--primary-bg);
    }
    .btn-secondary {
      background: var(--surface-muted);
      color: var(--text);
      border: 1px solid var(--border);
    }
    .theme-btn {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      inline-size: 2.35rem;
      block-size: 2.35rem;
      padding: 0;
      border-radius: 999px;
      background: var(--surface-muted);
      color: var(--text);
      border: 1px solid var(--border);
    }
    .theme-btn:hover {
      border-color: var(--muted);
    }
    .theme-btn svg {
      inline-size: 1.15rem;
      block-size: 1.15rem;
      stroke: currentColor;
      fill: none;
      stroke-width: 2;
      stroke-linecap: round;
      stroke-linejoin: round;
    }
    .icon-sun { display: none; }
    .icon-moon { display: block; }
    @media (prefers-color-scheme: dark) {
      :root:not(:has(> head > meta[name="color-scheme"][content="light"])) .icon-sun {
        display: block;
      }
      :root:not(:has(> head > meta[name="color-scheme"][content="light"])) .icon-moon {
        display: none;
      }
    }
    :root:has(> head > meta[name="color-scheme"][content="dark"]) .icon-sun {
      display: block;
    }
    :root:has(> head > meta[name="color-scheme"][content="dark"]) .icon-moon {
      display: none;
    }
    .badge {
      display: inline-flex;
      align-items: center;
      padding: 0.2rem 0.65rem;
      border-radius: 999px;
      font-size: 0.75rem;
      font-weight: 600;
    }
    .badge-ok { background: var(--ok-bg); color: var(--ok); }
    .badge-warn { background: var(--warn-bg); color: var(--warn); }
    .badge-err { background: var(--err-bg); color: var(--err); }
    .quote-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(165px, 1fr));
      gap: 0.75rem;
      margin-block-end: 1.25rem;
    }
    .metric-box {
      background: var(--surface-muted);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 0.8rem;
    }
    .metric-box .label {
      font-size: 0.75rem;
      color: var(--muted);
    }
    .metric-box .value {
      font-size: 1rem;
      font-weight: 700;
      margin-block-start: 0.25rem;
      font-variant-numeric: tabular-nums;
    }
    .section-card {
      background: var(--surface-muted);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 1rem 1.1rem;
      margin-block-end: 0.85rem;
    }
    .section-header {
      display: flex;
      flex-wrap: wrap;
      justify-content: space-between;
      align-items: center;
      gap: 0.5rem;
      margin-block-end: 0.35rem;
    }
    .req-quote {
      color: var(--muted);
      font-size: 0.86rem;
      margin-block-end: 0.55rem;
      padding-inline-start: 0.65rem;
      border-inline-start: 2px solid var(--border);
    }
    .claims-list, .gaps-list, .assumptions-list {
      margin: 0.4rem 0;
      padding-inline-start: 1.2rem;
      font-size: 0.9rem;
    }
    .claims-list li { margin-block-end: 0.35rem; }
    .gaps-list li { color: var(--warn); margin-block-end: 0.25rem; }
    details {
      margin-block-start: 0.6rem;
      font-size: 0.82rem;
      color: var(--muted);
    }
    details summary {
      cursor: pointer;
      font-weight: 500;
    }
    .evidence-item {
      padding: 0.55rem 0;
      border-block-start: 1px solid var(--border);
      margin-block-start: 0.45rem;
    }
    .status-banner {
      padding: 0.75rem 1rem;
      border-radius: 8px;
      margin-block-top: 1rem;
      font-size: 0.88rem;
      border: 1px solid var(--border);
    }
    .empty-state {
      color: var(--muted);
      font-size: 0.92rem;
      padding: 1.5rem 0.5rem;
    }
  </style>
</head>
<body>
  <header>
    <div class="header-inner">
      <div>
        <h1>Meridian Cloudworks — Proposal Assistant</h1>
        <p>Automated RFP Response &amp; Deterministic Commercial Quote Generator</p>
      </div>
      <button id="theme-toggle" class="theme-btn" type="button" aria-label="Toggle light and dark theme" title="Toggle theme">
        <svg class="icon-sun" viewBox="0 0 24 24" aria-hidden="true">
          <circle cx="12" cy="12" r="4"></circle>
          <path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M6.34 17.66l-1.41 1.41M19.07 4.93l-1.41 1.41"></path>
        </svg>
        <svg class="icon-moon" viewBox="0 0 24 24" aria-hidden="true">
          <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"></path>
        </svg>
      </button>
    </div>
  </header>

  <main>
    <section class="steps-bar" aria-label="How the proposal assistant works">
      <div class="step-item">
        <div class="step-num">Step 1 • Commercial Engine</div>
        <div class="step-title">Deterministic Rate-Card Pricing</div>
        <p class="step-desc">Extracts server counts, support terms, and discounts to compute an exact INR quote using official rate cards—never guessed by AI.</p>
      </div>
      <div class="step-item">
        <div class="step-num">Step 2 • Grounded Drafting</div>
        <div class="step-title">Evidence-Backed Responses</div>
        <p class="step-desc">Retrieves relevant Meridian product specs and past case studies to answer each customer requirement with traceable citations.</p>
      </div>
      <div class="step-item">
        <div class="step-num">Step 3 • Compliance Guardrails</div>
        <div class="step-title">Verification &amp; Auto-Repair</div>
        <p class="step-desc">Checks every section against 7 company policy rules and automatically rewrites any flagged section before exporting to Word (.docx).</p>
      </div>
    </section>

    <div class="grid-2">
      <section class="card" aria-labelledby="input-heading">
        <h2 id="input-heading">Customer RFP Input</h2>
        <div class="form-row">
          <div>
            <label for="preset-select">Sample Customer RFPs</label>
            <select id="preset-select"></select>
          </div>
          <div>
            <label for="rfp-textarea">Request for Proposal (RFP) Text</label>
            <textarea id="rfp-textarea" placeholder="Paste customer RFP requirements, server counts, target cloud platform, timeline, and pricing requests..."></textarea>
          </div>
          <div class="controls-grid">
            <div>
              <label for="condition-select">Compliance Repair Mode</label>
              <select id="condition-select">
                <option value="targeted_section">Targeted Section Repair (Recommended)</option>
                <option value="whole_document">Rewrite Entire Draft on Failure</option>
                <option value="none">Single Draft Pass (No Auto-Repair)</option>
              </select>
            </div>
            <div>
              <label for="mode-select">Drafting Engine</label>
              <select id="mode-select">
                <option value="nim">Live AI Generation</option>
                <option value="demo">Instant Offline Preview</option>
              </select>
            </div>
          </div>
          <p id="condition-hint" class="field-hint">
            Verifies every section against company policy and rewrites only the specific sections that need correction.
          </p>
          <div class="actions-row">
            <button id="run-btn" class="btn-primary" type="button">Generate Proposal</button>
            <a id="download-link" href="/api/download" style="display:none; text-decoration:none;">
              <button class="btn-secondary" type="button">Download Word Document (.docx)</button>
            </a>
          </div>
        </div>
        <div id="status-msg" class="status-banner" style="display:none;"></div>
      </section>

      <section class="card" aria-labelledby="output-heading">
        <h2 id="output-heading">
          <span>Generated Proposal &amp; Quote</span>
          <span id="summary-badges"></span>
        </h2>
        <div id="output-container">
          <div class="empty-state">
            Choose a sample RFP on the left (or paste your own) and click <strong>Generate Proposal</strong> to calculate the commercial quote and draft verified responses.
          </div>
        </div>
      </section>
    </div>
  </main>

  <script>
    const presetSelect = document.getElementById('preset-select');
    const rfpTextarea = document.getElementById('rfp-textarea');
    const conditionSelect = document.getElementById('condition-select');
    const conditionHint = document.getElementById('condition-hint');
    const modeSelect = document.getElementById('mode-select');
    const runBtn = document.getElementById('run-btn');
    const downloadLink = document.getElementById('download-link');
    const statusMsg = document.getElementById('status-msg');
    const outputContainer = document.getElementById('output-container');
    const summaryBadges = document.getElementById('summary-badges');
    const themeToggle = document.getElementById('theme-toggle');

    const CONDITION_HINTS = {
      targeted_section: 'Verifies every section against company policy and rewrites only the specific sections that need correction.',
      whole_document: 'If any section fails a policy check, regenerates the entire proposal draft from scratch.',
      none: 'Drafts each section once and reports policy verification status without automatic rewriting.'
    };

    let presets = [];

    function escapeHtml(str) {
      return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;');
    }

    themeToggle.addEventListener('click', () => {
      const meta = document.querySelector('meta[name="color-scheme"]');
      const sysDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
      const stored = localStorage.getItem('color-scheme');
      const currentDark = stored ? stored === 'dark' : sysDark;
      const target = currentDark ? 'light' : 'dark';
      const matchesSys = (target === 'dark') === sysDark;
      try {
        if (matchesSys) {
          localStorage.removeItem('color-scheme');
          meta.content = 'light dark';
        } else {
          localStorage.setItem('color-scheme', target);
          meta.content = target;
        }
      } catch (e) {
        meta.content = target;
      }
    });

    conditionSelect.addEventListener('change', () => {
      conditionHint.textContent = CONDITION_HINTS[conditionSelect.value] || '';
    });

    async function loadPresets() {
      const res = await fetch('/api/presets');
      const data = await res.json();
      presets = data.presets || [];
      presetSelect.innerHTML = presets.map((p, idx) =>
        `<option value="${idx}">${escapeHtml(p.label)}</option>`
      ).join('');
      if (presets.length) {
        rfpTextarea.value = presets[0].text;
      }
    }

    presetSelect.addEventListener('change', () => {
      const chosen = presets[Number(presetSelect.value)];
      if (chosen) rfpTextarea.value = chosen.text;
    });

    function renderResult(data) {
      const strictBadge = data.strict_compliance
        ? `<span class="badge badge-ok">All ${data.total_sections} Sections Policy-Verified</span>`
        : `<span class="badge badge-warn">${data.verified_sections} of ${data.total_sections} Sections Verified</span>`;
      summaryBadges.innerHTML = strictBadge;

      const q = data.quote;
      const assumptionsHtml = (data.assumptions || []).map(a =>
        `<li>${escapeHtml(a)}</li>`
      ).join('');

      const sectionsHtml = (data.sections || []).map(sec => {
        const badge = sec.final_passed
          ? `<span class="badge badge-ok">Verified</span>`
          : `<span class="badge badge-err">Needs Review</span>`;
        const repairedNote = (!sec.initial_passed && sec.final_passed)
          ? `<span class="badge badge-warn">Auto-Repaired</span>`
          : '';
        const statusBadge = `<span class="badge badge-secondary" style="border:1px solid var(--border);">${escapeHtml(sec.status_label)}</span>`;
        const claimsHtml = (sec.claims || []).map(c =>
          `<li>${escapeHtml(c.text)} <span style="color:var(--muted); font-size:0.82rem;">[${(c.evidence_ids || []).map(escapeHtml).join(', ')}]</span></li>`
        ).join('');
        const gapsHtml = (sec.gaps || []).map(g =>
          `<li>${escapeHtml(g)}</li>`
        ).join('');
        const issuesHtml = (sec.final_issues || []).map(i =>
          `<div style="color: var(--err); font-size:0.84rem; margin-block-start:0.25rem;">• Policy check: ${escapeHtml(i.detail)}</div>`
        ).join('');
        const evidenceHtml = (sec.evidence || []).map(ev =>
          `<div class="evidence-item"><strong>[${escapeHtml(ev.evidence_id)}] ${escapeHtml(ev.source_file)} — ${escapeHtml(ev.section)}</strong><br>${escapeHtml(ev.text)}</div>`
        ).join('');

        return `
          <div class="section-card">
            <div class="section-header">
              <strong>Requirement ${escapeHtml(sec.display_number)}: ${escapeHtml(sec.topic)}</strong>
              <div style="display:flex; gap:0.4rem; flex-wrap:wrap;">${statusBadge} ${repairedNote} ${badge}</div>
            </div>
            <div class="req-quote">&ldquo;${escapeHtml(sec.detail)}&rdquo;</div>
            ${claimsHtml ? `<ul class="claims-list">${claimsHtml}</ul>` : ''}
            ${gapsHtml ? `<ul class="gaps-list">${gapsHtml}</ul>` : ''}
            ${issuesHtml}
            <details>
              <summary>Supporting Reference Documents (${(sec.evidence || []).length})</summary>
              ${evidenceHtml}
            </details>
          </div>
        `;
      }).join('');

      outputContainer.innerHTML = `
        <div class="quote-grid">
          <div class="metric-box"><div class="label">Migration Subtotal</div><div class="value">${escapeHtml(q.migration_subtotal)}</div></div>
          <div class="metric-box"><div class="label">Managed Support</div><div class="value">${escapeHtml(q.support_subtotal)}</div></div>
          <div class="metric-box"><div class="label">Security Posture (CSPS)</div><div class="value">${escapeHtml(q.csps_subtotal)}</div></div>
          <div class="metric-box"><div class="label">Negotiated Discount</div><div class="value">${escapeHtml(q.negotiated_discount)}</div></div>
          <div class="metric-box"><div class="label">Total Quote (excl. GST)</div><div class="value">${escapeHtml(q.total)}</div></div>
        </div>
        ${assumptionsHtml ? `<div style="margin-block-end: 1.25rem;"><strong>Commercial Assumptions &amp; Policy Notes</strong><ul class="assumptions-list">${assumptionsHtml}</ul></div>` : ''}
        <div><strong style="display:block; margin-block-end:0.65rem;">Requirement-by-Requirement Response (${data.sections.length})</strong>${sectionsHtml}</div>
      `;
    }

    runBtn.addEventListener('click', async () => {
      runBtn.disabled = true;
      statusMsg.style.display = 'block';
      statusMsg.style.background = 'var(--surface-muted)';
      statusMsg.style.color = 'var(--text)';
      statusMsg.textContent = modeSelect.value === 'nim'
        ? 'Drafting proposal responses and verifying policy compliance (typically 20–45 seconds)...'
        : 'Generating instant offline preview...';
      try {
        const res = await fetch('/api/generate', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            rfp_text: rfpTextarea.value,
            condition: conditionSelect.value,
            mode: modeSelect.value,
          }),
        });
        const data = await res.json();
        if (!res.ok) {
          throw new Error(data.error || 'Generation request failed');
        }
        renderResult(data);
        downloadLink.style.display = 'inline-block';
        statusMsg.style.background = 'var(--ok-bg)';
        statusMsg.style.color = 'var(--ok)';
        statusMsg.textContent = `Proposal ready (${data.verified_sections} of ${data.total_sections} sections verified). Click "Download Word Document (.docx)" above to save.`;
      } catch (err) {
        statusMsg.style.background = 'var(--err-bg)';
        statusMsg.style.color = 'var(--err)';
        statusMsg.textContent = `Unable to generate proposal: ${err.message}`;
      } finally {
        runBtn.disabled = false;
      }
    });

    loadPresets();
  </script>
</body>
</html>
"""


def make_handler(root: Path = ROOT):
    class ProposalRequestHandler(BaseHTTPRequestHandler):
        def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
            return

        def _send_json(self, payload: dict[str, Any], status: int = HTTPStatus.OK) -> None:
            raw = json.dumps(payload).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def do_GET(self) -> None:  # noqa: N802
            if self.path in ("/", "/index.html"):
                raw = INDEX_HTML.encode("utf-8")
                self.send_response(HTTPStatus.OK)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)
                return
            if self.path == "/api/presets":
                self._send_json(build_presets(root))
                return
            if self.path == "/api/download":
                docx_path = root / "proposal.docx"
                if not docx_path.exists():
                    self._send_json(
                        {"error": "proposal.docx has not been generated yet."},
                        status=HTTPStatus.NOT_FOUND,
                    )
                    return
                raw = docx_path.read_bytes()
                self.send_response(HTTPStatus.OK)
                self.send_header(
                    "Content-Type",
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                )
                self.send_header(
                    "Content-Disposition", 'attachment; filename="proposal.docx"'
                )
                self.send_header("Content-Length", str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)
                return
            self._send_json({"error": "Not found"}, status=HTTPStatus.NOT_FOUND)

        def do_POST(self) -> None:  # noqa: N802
            if self.path != "/api/generate":
                self._send_json({"error": "Not found"}, status=HTTPStatus.NOT_FOUND)
                return
            length = int(self.headers.get("Content-Length", "0"))
            try:
                body = json.loads(self.rfile.read(length).decode("utf-8") or "{}")
                payload = execute_proposal_request(
                    rfp_text=str(body.get("rfp_text", "")),
                    condition_str=str(body.get("condition", "targeted_section")),
                    mode=str(body.get("mode", "nim")),
                    root=root,
                )
                self._send_json(payload)
            except Exception as exc:  # noqa: BLE001
                self._send_json(
                    {"error": f"{type(exc).__name__}: {exc}"},
                    status=HTTPStatus.BAD_REQUEST,
                )

    return ProposalRequestHandler


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the Meridian Proposal Assistant web UI"
    )
    parser.add_argument("--host", default="127.0.0.1", help="Bind host")
    parser.add_argument("--port", type=int, default=8000, help="Bind port")
    return parser


def main() -> None:
    args = _parser().parse_args()
    server = ThreadingHTTPServer((args.host, args.port), make_handler(ROOT))
    print(f"Meridian Proposal Assistant UI running at http://{args.host}:{args.port}")
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
