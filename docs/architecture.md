# Architecture

Supplier data goes in, and a draft due diligence statement (DDS) comes out for a human to approve.

**The main rule:** the LLM decides and explains, and code does the calculating. Coordinates and personal data never reach the LLM.

## Part 1: checking a shipment

```text
                       Shipment file (supplier data)
                                     │
                                     ▼
┌──────────────────────────────────────────────────────────────┐
│ Entry: CLI or FastAPI gateway                                │
└──────────────────────────────┬───────────────────────────────┘
                               ▼
┌──────────────────────────────────────────────────────────────┐
│ PII guardrail (Presidio)                                     │
│ Names, phones, IDs become pseudonyms before every LLM call   │
└──────────────────────────────┬───────────────────────────────┘
                               ▼
┌──────────────────────────────────────────────────────────────┐
│ Orchestrator agent (LLM)                                     │
│ Splits the work, reads supplier notes, combines verdicts     │
└──────────────┬───────────────────────────────┬───────────────┘
               ▼                               ▼
     ┌──────────────────┐            ┌──────────────────┐
     │ Geo subagent     │            │ Forest subagent  │
     │ (LLM)            │            │ (LLM)            │
     └────────┬─────────┘            └────────┬─────────┘
              │ sends: plot IDs               │ gets back: results
══════════════╪═══════════════════════════════╪════════════════
              │ DATA BOUNDARY: coordinates stay below
              ▼                               ▼
     ┌──────────────────┐            ┌──────────────────┐
     │ geo-mcp (code)   │            │ forest-mcp (code)│
     └────────┬─────────┘            └────────┬─────────┘
              ▼                               ▼
     ┌──────────────────┐            ┌──────────────────┐
     │ Plots, borders   │            │ UMD tree cover   │
     │                  │            │ loss (cached)    │
     └──────────────────┘            └──────────────────┘
```

Each subagent may only use its own MCP server. For example, the geo subagent can't call forest-mcp, and the orchestrator has no MCP tools at all.

The planned regulation agent became a lookup table in code (`src/eudr/risk.py`). A country's risk class is a fact from an EU list, so there is nothing for an LLM to decide.

Personal data is handled in two ways. Structured fields, like `farmer_phone`, are never given to an agent at all. Free text, like supplier notes, has to be read by an agent, so it goes through the PII guardrail first.

## Part 2: from results to a statement

```text
      Verdicts from the orchestrator
                     │
                     ▼
┌────────────────────────────────────────────┐
│ Risk decision (code, no LLM)               │
└────────────────────┬───────────────────────┘
                     ▼
┌────────────────────────────────────────────┐
│ Status: awaiting_review                    │
│ A HUMAN approves or rejects                │
└──────────┬─────────────────────┬───────────┘
        approve                reject
           ▼                     ▼
┌─────────────────────┐   ┌─────────────────┐
│ DDS draft           │   │ Stop, no DDS    │
└──────────┬──────────┘   └─────────────────┘
  LLM: risk summary only
  code: everything else,
  including geolocation
           ▼
  A human files it in the EU system
  (out of scope for this project)
```

## What each part does, and its status

| Part | Job | Status |
| --- | --- | --- |
| geo-mcp | Validates geometry, measures area, applies the 4 ha rule, finds the country | Built and tested |
| forest-mcp | Reports tree cover loss after 2020 per plot, from a cache of UMD data | Built and tested |
| Orchestrator, geo and forest subagents | Run the check and return a structured verdict per plot and supplier | Built and tested |
| PII guardrail | Replaces personal data in supplier notes with placeholders before the LLM sees them, and restores it for the human reviewer | Built and tested |
| Risk decision | Country risk class from a table; blocks a shipment on any failed plot or legality gap | Built and tested |
| Human review and DDS draft | Stores checks pseudonymized; drafts the DDS only after approval | Built and tested |
| Evals | Score the agent against 25 cases with known answers | Built, 25/25 over 3 runs |
| CLI and FastAPI gateway | Start, review and approve checks from a terminal or over HTTP | Built and tested |
| Cost tracker | Logs tokens and cost per run and per agent | Built and tested |
| Docker | `docker compose up` starts the API | Built and tested |
| Regulation RAG, supplier memory, Postgres, Langfuse | Cut for v1, see `production-considerations.md` | Cut |
