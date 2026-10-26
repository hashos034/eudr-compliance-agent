# EUDR agent: week plan

Oct 25, 2026 · @hassan

## Overview

On Sunday 1 November there is a working EUDR compliance agent on your GitHub. Supplier data goes in and a draft due diligence statement comes out, built with MCP servers, subagents, a PII guardrail, memory, human review and evals.

- **Time:** about 40 hours, so 6 to 7 hours a day for 7 days.
- **Where:** locally on your laptop, in a public GitHub repo. Everything runs in Docker, so anyone can start it with one command.
- **Design principle:** the LLM decides and explains, code calculates. Coordinates and personal data never reach the LLM.

Every day follows the same rhythm:

1. **Read (45 min):** that day's material from the reading list.
2. **Build (5 to 6 hours):** that day's tasks, in small commits.
3. **Wrap up (30 min):** push everything, write a short note for LinkedIn, and check you meet the "Done when" line.

## Preparation (Monday morning, 1.5 hours)

Get all accounts and tools ready before you start building, so nothing blocks you on Monday.

- [ ] Create an API key in the [Claude Console](https://platform.claude.com) and set a spending limit, for example €20 for the week.
- [ ] Install Python 3.12 and [uv](https://docs.astral.sh/uv/) (a fast package manager).
- [ ] Install [Docker Desktop](https://www.docker.com/products/docker-desktop/).
- [ ] Install [Claude Code](https://code.claude.com/docs). The Agent SDK uses it as its runtime, and you can use it as a pair programmer.
- [ ] Create a free [Global Forest Watch](https://www.globalforestwatch.org) account and an API key for the Data API.
- [ ] Create a free [Langfuse](https://langfuse.com) account for tracing.
- [ ] Create a public GitHub repo `eudr-compliance-agent`, with a README, a Python .gitignore and an MIT license.
- [ ] Set up your editor: VS Code or Cursor.

## Daily schedule

After Tuesday you already have a working demo. Everything after that is extension, and Sunday is buffer.

### Monday 26 Oct: foundations and geo-mcp

**Learn:** MCP basics, Shapely and the EUDR geolocation requirements.

- [ ] Set up the repo structure and uv project, first commit.
- [ ] Create fake test data: 5 suppliers and 20 plots in GeoJSON. Include a few invalid ones, a few points that are too large and a few in deforested areas, with made-up farmer names and phone numbers.
- [ ] Build geo-mcp with FastMCP: `validate_geometry`, `calculate_area_ha`, `check_point_or_polygon` (above 4 ha it must be a polygon) and `check_country`.
- [ ] Write unit tests with pytest.
- [ ] Test the server with the MCP Inspector.

**Done when:** you can validate a plot in the Inspector and get the right error message back.

### Tuesday 27 Oct: orchestrator and first subagent

**Learn:** the Claude Agent SDK (agent loop, subagents, allowed tools) and the article on effective agents.

- [ ] Build an orchestrator that reads a shipment and splits up the work.
- [ ] A geo subagent that may only use geo-mcp tools (per-agent authorization).
- [ ] Structured output with Pydantic: per plot approved or rejected, with a reason.
- [ ] Cost tracker: log tokens and cost per run and per agent.
- [ ] CLI: `python -m eudr check data/shipments/shipment_01.json`.

**Done when:** one command checks a shipment from start to finish. This is your first demo.

### Wednesday 28 Oct: deforestation check

**Learn:** the Global Forest Watch Data API, the tree cover loss dataset and the cut-off date of 31 December 2020.

- [ ] Build forest-mcp: `check_forest_loss` returns the hectares of forest loss after 2020 per plot.
- [ ] Cache API responses, so the demo and evals don't depend on an external API.
- [ ] A deforestation subagent that may only use forest-mcp tools.
- [ ] The orchestrator combines the geo and deforestation results into a risk score per plot.

**Done when:** a test plot with known forest loss comes out of the run as high risk.

### Thursday 29 Oct: API gateway and PII guardrail

**Learn:** FastAPI and Presidio (analyzer, anonymizer, custom recognizers).

- [ ] FastAPI app with `POST /checks` and `GET /checks/{id}`, API key authentication and rate limiting.
- [ ] PII guardrail with Presidio: pseudonymize names, phone numbers and ID numbers before every LLM call, including in tool results.
- [ ] Never send coordinates to the LLM: agents get only plot IDs and results.
- [ ] A test that proves there is no PII in the LLM input.

**Done when:** you start a check through the API and see only pseudonyms in the logs.

### Friday 30 Oct: memory, regulation and review

**Learn:** Postgres with pgvector, RAG basics and human-in-the-loop.

- [ ] Postgres + pgvector in Docker Compose, as a session store (status per check) and memory (history per supplier).
- [ ] Build regulation-mcp: `search_regulation` searches the EUDR text and FAQ and cites the source with every answer.
- [ ] A regulation subagent that gives the origin country's risk class and the relevant articles.
- [ ] Review step: a check gets the status `awaiting_review` and is approved or rejected via `POST /checks/{id}/approve` or `/reject`.
- [ ] Generate the DDS draft only after approval.

**Done when:** a check ends in an approved DDS draft.

### Saturday 31 Oct: evals, tracing and Docker

**Learn:** tracing with Langfuse and how to set up an eval set.

- [ ] An eval set with 15 to 20 test plots and their expected outcome, plus a script that calculates the score.
- [ ] Langfuse tracing of prompts, agent calls and tool calls.
- [ ] Get everything running with `docker compose up`.
- [ ] Write the README: problem, architecture diagram, quickstart, eval score, cost per check and a "Production considerations" section.

**Done when:** someone else can clone the repo and run it with one command.

### Sunday 1 Nov: buffer and launch

- [ ] Finish whatever ran over.
- [ ] Record a 60-second demo GIF: upload, agents, review, DDS.
- [ ] Clean up the repo and tag it `v1.0`.
- [ ] Publish the final LinkedIn post and add the project to your CV.

**Done when:** the repo is public and the post is live.

## Reading list

Each day, read only what is in the table. Sources marked "reference" you open only when you get stuck.

| Day | Topic | Source | Time |
| --- | --- | --- | --- |
| Before | What good agents look like | [Building effective agents (Anthropic)](https://www.anthropic.com/research/building-effective-agents) | 20 min |
| Mon | What MCP is | [Model Context Protocol](https://modelcontextprotocol.io) | 15 min |
| Mon | Your first MCP server | [FastMCP tutorial](https://gofastmcp.com/tutorials/create-mcp-server) | 20 min |
| Mon | Official MCP SDK | [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk) | reference |
| Mon | Geometry in Python | [Shapely documentation](https://shapely.readthedocs.io) | reference |
| Mon | What the EUDR requires | [EUDR FAQ (European Commission)](https://environment.ec.europa.eu/publications/frequently-asked-questions-deforestation-regulation_en) | 30 min |
| Tue | Building agents | [Agent SDK overview](https://platform.claude.com/docs/en/agent-sdk/overview) | 20 min |
| Tue | The SDK's Python API | [Agent SDK Python reference](https://code.claude.com/docs/en/agent-sdk/python) | reference |
| Wed | Forest loss data | [GFW: tree cover loss](https://data-api.globalforestwatch.org/dataset/umd_tree_cover_loss) | 15 min |
| Thu | Building an API | [FastAPI tutorial](https://fastapi.tiangolo.com/tutorial/) | 30 min |
| Thu | Detecting and masking PII | [Microsoft Presidio](https://microsoft.github.io/presidio/) | 30 min |
| Fri | The EUDR in practice | [EUDR implementation (European Commission)](https://green-business.ec.europa.eu/deforestation-regulation-implementation_en) | 15 min |
| Fri | Vector search in Postgres | [pgvector](https://github.com/pgvector/pgvector) | 15 min |
| Sat | Tracing and evals | [Langfuse documentation](https://langfuse.com/docs) | 20 min |

## Repo structure

Each MCP server stands on its own, so you can test and reuse it separately. The agent code lives in `src/eudr`.

```text
eudr-compliance-agent/
├── README.md
├── docker-compose.yml
├── pyproject.toml
├── data/
│   ├── shipments/           fake shipments (JSON)
│   └── plots/               fake plots (GeoJSON)
├── mcp_servers/
│   ├── geo_mcp/
│   ├── forest_mcp/
│   └── regulation_mcp/
├── src/eudr/
│   ├── __main__.py          CLI
│   ├── agents/              orchestrator + subagents
│   ├── gateway/             FastAPI app
│   ├── guardrails/          PII (Presidio)
│   ├── memory/              Postgres, session store
│   ├── review/              human review
│   └── cost_tracker.py
├── evals/
│   ├── cases.json
│   └── run_evals.py
├── tests/
└── docs/
    ├── architecture.png
    └── production-considerations.md
```

## LinkedIn posts

Four posts spread over the week tell a story, instead of one isolated post at the end.

| When | Topic | Hook |
| --- | --- | --- |
| Mon 26 Oct | Announcement | In two months, coffee importers must prove their beans don't come from deforested land. This week I'm building an AI agent that checks that. |
| Tue 27 Oct | First demo | Screenshot of the first run, plus what one check costs. |
| Thu 29 Oct | Design choice | Why farmers' coordinates never go to the LLM: the LLM decides, code calculates. |
| Sun 1 Nov | Launch | Demo GIF, architecture diagram, eval score and the link to the repo. |

## Risks and fallback plan

If you fall behind, cut in this order. Always keep the PII guardrail, the evals and the README: those are your selling points.

1. Regulation RAG: replace it with a fixed table of risk class per country.
2. Per-supplier memory: keep only the session store.
3. Langfuse tracing: keep the cost tracker.
4. Rate limiting in the gateway.

Known pitfalls:

- **Global Forest Watch is slow or down:** download the data for one coffee region in advance and use it as a local file. That's enough for the demo.
- **You get stuck on the Agent SDK:** switch to the plain Messages API with tool use. The architecture stays the same.
- **Costs are climbing:** use a smaller model like Haiku for subagents and tests.
- **A task takes twice as long as planned:** mark it "later" and move on to the next one.

## Sources

- [DHL: EUDR requirements for exporters](https://www.dhl.com/discover/en-br/regulatory-affairs/eudr-export-european-union): applies from 30 December 2026.
- [NKG: EUDR](https://www.nkg.net/eudr): due diligence statement with the geolocation of every plot.
