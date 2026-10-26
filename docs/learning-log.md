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
