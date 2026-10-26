# EUDR Compliance Agent

A one-week build (26 Oct – 1 Nov 2026): an agent that checks supplier data for coffee shipments against the EU Deforestation Regulation and drafts a due diligence statement (DDS) for a human to approve.

- The plan: `docs/weekplan.md` (in Dutch). The problem: `docs/problem.md`.
- What Hassan has learned so far: `docs/learning-log.md`.

## Design rules (do not break these)

- The LLM decides and explains. **Code does the calculating** (areas, geometry, forest loss, scores).
- **Coordinates and personal data never reach the LLM.** Agents see plot IDs and results only.
- Every MCP server in `mcp_servers/` stands on its own and can be tested by itself.

## How we work: teaching mode

Hassan is a first-year master's student and this is their first real project. The goal is to **learn AI engineering tools** and end up with a portfolio piece, not only to ship code.

- **Explain before building.** For each new concept (MCP, subagents, Pydantic, RAG and so on), give a short plain-language explanation and say why it is used here, before writing code for it.
- **Small steps.** Build one piece, run it, look at the result together, commit. No large unexplained code drops.
- **Hassan types some of it.** For core pieces, suggest Hassan writes the code with hints, or fills in a stub. Generate the boilerplate.
- **Name the tool.** When we use something new (uv, pytest, MCP Inspector, Docker Compose), say what it is and what it replaces.
- **Check understanding.** At the end of each day's block, ask 1–2 short questions about what we built.
- **Daily rhythm** (from the weekplan): read, build, wrap up. Wrap-up means: push, add an entry to `docs/learning-log.md`, and draft notes for LinkedIn.
- Commits: small, clear messages, so the history itself tells the story.

## Stack

Python 3.12 · uv · FastMCP · Claude Agent SDK · Pydantic · FastAPI · Presidio · Postgres + pgvector · Langfuse · Docker Compose · pytest
