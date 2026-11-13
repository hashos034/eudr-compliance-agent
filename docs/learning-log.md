# Learning log

One entry per day: what I built, which concepts I learned, what went wrong, and one LinkedIn-worthy insight.

## Mon 26 Oct: foundations and geo-mcp

- **Built:** a uv project; fake data (5 suppliers, 20 plots, 2 shipments) with planted mistakes; geo-mcp, an MCP server with 4 tools (`validate_geometry`, `calculate_area_ha`, `check_point_or_polygon`, `check_country`); 17 pytest tests; tested it by hand in the MCP Inspector.
- **Concepts:**
  - **uv** manages Python versions, the venv and packages in one tool. `uv run` always runs inside the project's venv.
  - **MCP** is a standard way to give an LLM tools. The server holds the data and does the calculating; the LLM only gets results.
  - The tools take a **plot ID, not coordinates**, so coordinates never reach the LLM (whose input is sent to an outside API).
  - **Shapely** checks shapes but auto-closes open rings and doesn't know lat/lon ranges, so those checks run on the raw coordinates first.
  - **"Shapely checks the shape, pyproj measures the size":** Shapely's area is in square degrees, which mean different sizes in different places. pyproj measures on the real Earth.
  - **Natural Earth** country borders + a point-in-polygon test to find which country a plot is in.
  - Why an agent at all: code handles the hard rules; the agent handles messy input, judgment calls and explanations.
- **Stuck on:** at first I didn't see why we needed an MCP server instead of plain functions. Answer: the main reason is the data boundary to the LLM, plus per-agent permissions and testing each part separately.
- **LinkedIn insight:** my own rule ("coordinates never reach the LLM") was broken by an error message. Shapely's validity reason and my own range check both printed coordinates into the tool result. I only saw it by testing in the Inspector, so now a test calls every tool for every plot and fails if anything that looks like a coordinate comes back.

## Tue 3 Nov to Fri 13 Nov: from first demo to v1

- **Built:** the orchestrator with a geo subagent, a cost tracker and the CLI; the PII guardrail; forest-mcp with a cache of real tree cover loss data; a forest subagent; a risk decision in code; human review with a DDS draft; an eval set; a FastAPI gateway; Docker; the README.
- **Concepts:**
  - **Subagents with least privilege:** each agent gets only the tools of its own MCP server, and the run stops if the SDK reports any other tool.
  - **Structured output:** the agent's answer must fit a Pydantic schema, and code then checks that every plot and supplier got exactly one verdict.
  - **Pseudonymization, not anonymization:** names become `<PERSON_1>` for the LLM, and a separate lookup table brings them back for the human reviewer.
  - **Caching an external dataset:** the forest check reads a local cache, matched to each plot's shape by a hash, so a demo or eval never depends on a data provider being up.
  - **Evals scored in code:** the most important number is unsafe approvals, because a wrong approval is far worse than a wrong rejection.
  - **A human gate in code:** the DDS step refuses to run before approval, and refuses to approve a shipment whose risk isn't negligible.
- **Stuck on:** the two plots I planted as "deforested" did show heavy tree cover loss, but all of it before 2020, so under the EUDR they were legally clean. I had to find spots with real loss after the cut-off.
- **LinkedIn insight:** the cut-off date changes everything. A satellite image full of cleared forest can be perfectly compliant if the clearing happened in 2019, so "is there deforestation?" is the wrong question for the EUDR. The right one is "when?"
