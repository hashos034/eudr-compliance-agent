# Production considerations

This project is a working prototype on fake supplier data. This page lists what would have to change before a real importer could rely on it, roughly in order of importance.

## Data and accuracy

- **Forest data is a signal, not a verdict.** The forest check uses the University of Maryland's tree cover loss data (30 m pixels, one loss year per pixel). It can't tell deforestation from replanting, fire or a harvest of planted trees, and it misses loss under a cloudy season. A flagged plot needs a human or a second dataset, for example the JRC Global Forest Cover 2020 map the Commission recommends, or RADD alerts.
- **The year 2020 counts as before the cut-off.** The data gives only a year, so loss in 2020 can't be split around 31 December. A cautious operator might flag 2020 too.
- **The forest cache must be refreshed.** The cache is matched to each plot's shape by a hash, so a changed polygon is never matched to old data. But new loss years appear once a year, and the cache has to be rebuilt when they do.
- **Country risk comes from a table.** The table follows Implementing Regulation (EU) 2025/1093 and must be updated when the Commission reviews the list.
- **Legality is read from a free-text note.** In production the agent should check the documents themselves (titles, permits, tax certificates) and their expiry dates, not a colleague's summary of them.

## Personal data

- **The PII guardrail reduces risk but can't remove it.** It uses three layers: an NLP model, known values from our own data, and a final check in code. An unusual name that isn't in our data and that the model misses could still reach the LLM. Use a data processing agreement with zero data retention for the LLM provider.
- **The lookup table needs real protection.** Today it is a separate file that only its owner can read. In production it would be encrypted in a database, with access logs, and deleted when the check's retention period ends.
- **Retention.** The EUDR requires records to be kept for five years. That clashes with data minimisation under the GDPR, so retention needs a deliberate policy.

## Agents and LLM

- **Evals must grow.** The current set has 25 cases that were written alongside the tools, so a perfect score shows the plumbing and instructions work, not that the agent handles real-world mess. Add messy real notes, prompt injection attempts in notes, borderline forest loss and contradictory documents.
- **Cost and speed.** One check of a 4 to 9 plot shipment costs about $0.15 to $0.20 with Opus for every agent, and takes one to four minutes. Subagents that only call a tool and report could use a smaller model. Large shipments with hundreds of plots should be split into batches.
- **Non-determinism.** The LLM can answer differently on the same input. Code already checks that every plot and supplier gets exactly one verdict, and run the evals several times before each release.

## Service

- **Storage.** Checks are JSON files in a folder. Use Postgres for status, history per supplier and audit logs.
- **Jobs.** Checks run as FastAPI background tasks, which are lost if the server restarts. Use a job queue.
- **Access.** One shared API key is fine for a demo. Production needs per-user accounts, roles (only a compliance officer may approve) and rate limits.
- **Tracing.** The cost tracker logs tokens and cost per agent. A tracing tool like Langfuse would show each prompt, tool call and decision for audits.
- **Filing.** The DDS draft is Markdown with GeoJSON. Filing it in the EU information system (TRACES) through its API is out of scope.
