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
│ Splits the work, combines results, explains decisions        │
└────────┬─────────────────────┬─────────────────────┬─────────┘
         ▼                     ▼                     ▼
┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
│ Geo subagent     │  │ Forest subagent  │  │ Regulation agent │
│ (LLM)            │  │ (LLM)            │  │ (LLM)            │
└────────┬─────────┘  └────────┬─────────┘  └────────┬─────────┘
         │                     │                     │
         │  sends: plot IDs    │  gets back: results │
═════════╪═════════════════════╪═════════════════════╪══════════
         │  DATA BOUNDARY: coordinates stay below    │
         ▼                     ▼                     ▼
┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
│ geo-mcp          │  │ forest-mcp       │  │ regulation-mcp   │
│ (code)           │  │ (code)           │  │ (code)           │
└────────┬─────────┘  └────────┬─────────┘  └────────┬─────────┘
         ▼                     ▼                     ▼
┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
│ Plots, borders   │  │ Forest loss data │  │ Country risk     │
└──────────────────┘  └──────────────────┘  └──────────────────┘
```

Each subagent may only use its own MCP server. For example, the geo subagent can't call forest-mcp.

Personal data is handled in two ways. Structured fields, like `farmer_phone`, are never given to an agent at all. Free text, like supplier notes, has to be read by an agent, so it goes through the PII guardrail first.

## Part 2: from results to a statement

```text
      Results from the three subagents
                     │
                     ▼
┌────────────────────────────────────────────┐
│ Risk score per plot (code, no LLM)         │
└────────────────────┬───────────────────────┘
                     ▼
┌────────────────────────────────────────────┐
│ Status: awaiting_review                    │
│ A HUMAN approves or rejects                │
└──────────┬─────────────────────┬───────────┘
        approve                reject
           ▼                     ▼
┌─────────────────────┐   ┌─────────────────┐
│ DDS draft (LLM)     │   │ Stop, no DDS    │
└──────────┬──────────┘   └─────────────────┘
           ▼
  A human files it in the EU system
  (out of scope for this project)
```

## What each part does, and its status

| Part | Job | Status |
| --- | --- | --- |
| geo-mcp | Validates geometry, measures area, applies the 4 ha rule, finds the country | **Built and tested** |
| Orchestrator and geo subagent | Run the check and return a structured result per plot and supplier | **Built and tested** |
| CLI | Starts a check with one command | **Built and tested** |
| Cost tracker | Logs tokens and cost per run and per agent | **Built and tested** |
| PII guardrail | Replaces personal data in supplier notes with placeholders before the LLM sees them, and restores it for the human reviewer | **Built and tested** |
| forest-mcp and forest subagent | Report forest loss after 2020 per plot | To build |
| Risk score | Combines the results into a score per plot | To build |
| Human review and DDS draft | Generate the draft only after approval | To build |
| Evals | Score the agent against the expected outcomes | To build |
| FastAPI gateway | Offers the same check over HTTP | To build if time is left |
| Regulation agent and regulation-mcp | Give the country risk class and relevant articles | To build, proposed as a fixed table instead of RAG |
| Supplier memory, Postgres, Langfuse | History per supplier, storage, tracing | Proposed cut |
