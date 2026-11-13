# EUDR compliance agent

An AI agent that checks coffee supplier data against the **EU Deforestation Regulation (EUDR)** and drafts a due diligence statement for a human to approve.

From 30 December 2026, a company that brings coffee onto the EU market must prove it grew on land that wasn't deforested after 31 December 2020, and that it was produced legally. The proof is a due diligence statement (DDS) with the location of every plot the coffee came from. One container can hold beans from hundreds of small farms, so the supplier data arrives messy, incomplete and full of farmers' personal details. This project checks that data, flags the risky plots, and drafts the statement only after a person signs off.

> Built in a compressed sprint as my first AI engineering project. All supplier and farmer data is invented. The forest loss data is real.

## What it does

Output shortened:

```text
$ uv run python -m eudr check data/shipments/shipment_01.json

  P01  approved  ok                  Geo check passed, and no tree cover loss after 31 Dec 2020.
  P03  rejected  point_too_large     The plot is 5.5 ha but was given as a single point; over 4 ha needs a polygon.
  P04  rejected  country_mismatch    The supplier declared Ethiopia (ET) but the plot lies in Kenya (KE).
  P07  rejected  invalid_geometry    The plot boundary crosses itself, so the shape is invalid.
  P19  rejected  forest_loss         4.12 ha of tree cover loss after the cut-off: 0.08 ha in 2021, 2.29 ha in 2022, 1.76 ha in 2023.
  ...
Proof of legality (from supplier notes):

  SUP-001  documented  Land title documents and the 2026 tax certificate are on file.
  SUP-005  gap         Gilmar José Stedile's land lease expired in January and has not been renewed.

Risk (calculated in code):

  Country risk: BR standard, CO standard, ET standard
  BLOCKED  Plot P19 failed: forest_loss
  BLOCKED  Supplier SUP-005 has no proof of legality on file
  ...
```

A clean shipment can then be approved, and only then is a DDS drafted:

```text
$ uv run python -m eudr approve chk-963c328618de --reviewer "Demo Reviewer"
Approved. DDS draft written to checks/chk-963c328618de/dds_draft.md
```

## How it works

```text
 Shipment ──► PII guardrail ──► Orchestrator agent ──┬──► Geo subagent ────► geo-mcp ────► plots, country borders
              (Presidio)        reads supplier notes │
                                                     └──► Forest subagent ─► forest-mcp ─► UMD tree cover loss
                                       │                       ▲
                                       │        ═══════════════╪═══ data boundary: only plot IDs cross,
                                       ▼                            coordinates and names stay below
                         Risk decision (code) ──► human review ──► DDS draft
```

- **Agents** (Claude Agent SDK): an orchestrator delegates to two subagents, then combines their reports into one verdict per plot and reads each supplier's note for proof of legality.
- **MCP servers** (FastMCP): `geo-mcp` checks geometry, area, the 4 ha point-or-polygon rule and the country. `forest-mcp` reports tree cover loss after 2020. Each one stands alone and can be tested by itself.
- **Code, not the LLM**, does every calculation: areas, point-in-country tests, forest loss, the risk decision and the DDS layout.
- **Human review** is a hard gate. No DDS is drafted before approval, and code refuses to approve a shipment with any failed plot or legality gap.

More detail: [docs/architecture.md](docs/architecture.md).

## Design decisions

**The LLM decides and explains; code calculates.** An LLM is good at reading a messy note and explaining a result to a compliance officer, and bad at measuring a polygon on a curved Earth. So every number comes from a tool, and the agent's job is to call the tools, apply the rules and explain.

**Coordinates and personal data never reach the LLM.** The MCP tools take a plot ID, not coordinates, and return results without coordinates. Agents get no file or shell tools, so they can't read the data around the tools. A test calls every tool for every plot and fails if anything that looks like a coordinate comes back. The DDS needs the geolocation, so code adds it after the LLM step.

**PII guardrail in three layers.** Supplier notes are free text, so an agent has to read them. Before it does, Presidio replaces names, phone numbers, emails and national IDs with placeholders like `<PERSON_1>`. No single layer is enough: the NLP model finds unknown names but can split them, so known values from our own data are added, and a final check in code stops the run if a known value is still in the prompt. Checks are stored pseudonymized, the lookup table is kept in a separate owner-only file, and real names are restored only when a person views the check.

**Least privilege per agent.** The orchestrator has only the `Agent` tool. The geo subagent has only geo-mcp, and the forest subagent only forest-mcp. The run stops if the SDK reports any tool that wasn't chosen.

**A missing answer is never a clean answer.** If forest data is missing for a plot, or its shape changed since the data was cached, the result is "unknown" and the plot fails. Code also checks that the LLM returned exactly one verdict for every plot and supplier.

**A table, not RAG, for country risk.** A country's risk class is a fact from an EU list (Implementing Regulation 2025/1093). A lookup table can't hallucinate.

## Results

**Evals.** 25 cases with known answers: 20 plots (planted geometry errors, plots in the wrong country, real forest loss after 2020, and a trap plot with loss *before* 2020 that must pass) and 5 supplier notes. Scoring is plain code, not an LLM grading itself.

| Metric | Result (3 runs) |
| --- | --- |
| Plot verdicts correct | 20/20 in every run |
| Supplier legality correct | 5/5 in every run |
| Unsafe approvals (a failing case passed) | 0 |
| Cost per eval run (25 cases) | $0.29 to $0.35 |
| Time per eval run | about 55 seconds |

A perfect score on a small set I wrote myself shows the pipeline and instructions work. It doesn't prove the agent handles real-world mess; see [what's next](#whats-next).

**Cost per check.** A 4 to 9 plot shipment costs about $0.15 to $0.20 with Claude Opus for every agent, logged per agent in `logs/costs.jsonl`. Drafting the DDS adds about $0.03.

**Tests.** 94 pytest tests, none of which call the LLM: geometry, forest loss, the PII guardrail, the tool lockdown, the review gate, the DDS and the API.

## Quickstart

You need Python 3.12, [uv](https://docs.astral.sh/uv/) and an [Anthropic API key](https://platform.claude.com).

```bash
git clone https://github.com/hashos034/eudr-compliance-agent.git
cd eudr-compliance-agent
cp .env.example .env          # add your ANTHROPIC_API_KEY
uv sync
uv run pytest                 # free, no LLM calls
```

**CLI**

```bash
uv run python -m eudr check data/shipments/shipment_03.json   # the clean shipment
uv run python -m eudr list
uv run python -m eudr show <check_id>
uv run python -m eudr approve <check_id> --reviewer "Your Name"
uv run python -m eudr reject <check_id> --reviewer "Your Name" --reason "..."
```

**API with Docker**

```bash
docker compose up --build
export $(grep EUDR_API_KEY .env)
curl -H "X-API-Key: $EUDR_API_KEY" -H "Content-Type: application/json" \
     -d @data/shipments/shipment_03.json localhost:8000/checks
```

Then poll `GET /checks/{id}` until it is `awaiting_review`, and call `POST /checks/{id}/approve` and `GET /checks/{id}/dds`. Interactive docs are at http://localhost:8000/docs.

**Evals** (about $0.30 per run)

```bash
uv run python -m evals.run_evals --runs 3
```

**Inspect an MCP server on its own**

```bash
npx @modelcontextprotocol/inspector uv run python -m mcp_servers.geo_mcp.server
```

## Project structure

```text
mcp_servers/
  geo_mcp/            geometry, area, 4 ha rule, country (Shapely, pyproj, Natural Earth)
  forest_mcp/         tree cover loss after 2020, read from a local cache
    refresh_cache.py  rebuilds the cache from the UMD Global Forest Change rasters
src/eudr/
  agents/             orchestrator, subagents and their prompts
  guardrails/pii.py   Presidio pseudonymizer
  risk.py             country risk table and the risk decision
  review/             check store and the review steps
  dds.py              DDS draft
  gateway/app.py      FastAPI
  cost_tracker.py     tokens and cost per agent
evals/                cases and the scoring script
data/                 fake suppliers, plots and shipments
docs/                 problem, architecture, production considerations, learning log
```

## Stack

Python 3.12 · uv · Claude Agent SDK · FastMCP · Pydantic · Presidio · Shapely · pyproj · rasterio · FastAPI · Docker Compose · pytest

## What's next

- **Harder evals:** real, messy supplier notes, prompt injection attempts hidden in notes, borderline forest loss and expired documents.
- **A second forest dataset** (JRC Global Forest Cover 2020) to separate deforestation from replanting.
- **Postgres** for checks and supplier history, a job queue for long checks, and per-user roles for approval.
- **Tracing** with Langfuse for audits.

The full list, with the limits of the current data: [docs/production-considerations.md](docs/production-considerations.md).

## Data sources

- Tree cover loss: Hansen, M. C. et al. (2013), *High-Resolution Global Maps of 21st-Century Forest Cover Change*, University of Maryland, dataset GFC-2025-v1.13.
- Country borders: [Natural Earth](https://www.naturalearthdata.com).
- Country risk classes: Commission Implementing Regulation (EU) 2025/1093.

## License

MIT
