# EUDR-agent: weekplan

Oct 25, 2026 · @hassan

## Overzicht

Op zondag 1 november staat er een werkende EUDR-compliance agent op je GitHub. Er gaat leveranciersdata in en er komt een concept due diligence-verklaring uit, met MCP servers, subagents, een PII-guardrail, memory, menselijke review en evals.

- **Tijd:** ongeveer 40 uur, dus 6 tot 7 uur per dag, 7 dagen lang.
- **Waar:** lokaal op je laptop, in een publieke GitHub-repo. Alles draait in Docker, zodat iedereen het met één commando kan starten.
- **Ontwerpprincipe:** het LLM beslist en legt uit, code rekent. Coördinaten en persoonsgegevens gaan nooit naar het LLM.

Elke dag volgt hetzelfde ritme:

1. **Inlezen (45 min):** de leesstof van die dag uit de leeslijst.
2. **Bouwen (5 à 6 uur):** de taken van die dag, in kleine commits.
3. **Afsluiten (30 min):** alles pushen, een korte notitie voor LinkedIn, en checken of je aan de regel "Klaar als" voldoet.

## Voorbereiding (maandagochtend, 1,5 uur)

Zorg dat alle accounts en tools klaarstaan voordat je gaat bouwen, dan loop je maandag nergens op vast.

- [ ] API-key aanmaken in de [Claude Console](https://platform.claude.com) en een bestedingslimiet instellen, bijvoorbeeld €20 voor de week.
- [ ] Python 3.12 en [uv](https://docs.astral.sh/uv/) installeren (snelle package manager).
- [ ] [Docker Desktop](https://www.docker.com/products/docker-desktop/) installeren.
- [ ] [Claude Code](https://code.claude.com/docs) installeren. De Agent SDK gebruikt het als runtime, en je kunt het als pair programmer gebruiken.
- [ ] Gratis account bij [Global Forest Watch](https://www.globalforestwatch.org) aanmaken en een API-key voor de Data API aanmaken.
- [ ] Gratis [Langfuse](https://langfuse.com)-account aanmaken voor tracing.
- [ ] Publieke GitHub-repo `eudr-compliance-agent` aanmaken, met README, Python-.gitignore en MIT-licentie.
- [ ] Editor klaarzetten: VS Code of Cursor.

## Dagplanning

Na dinsdag heb je al een werkende demo. Alles daarna is uitbreiding, en zondag is buffer.

### Maandag 26 okt: fundament en geo-mcp

**Leren:** basis van MCP, Shapely en de geolocatie-eisen van de EUDR.

- [ ] Repo-structuur en uv-project opzetten, eerste commit.
- [ ] Nep-testdata maken: 5 leveranciers en 20 percelen in GeoJSON. Neem er een paar op die ongeldig zijn, een paar te grote punten en een paar in ontbost gebied, met verzonnen boerennamen en telefoonnummers.
- [ ] geo-mcp bouwen met FastMCP: `validate_geometry`, `calculate_area_ha`, `check_point_or_polygon` (boven 4 ha moet het een polygoon zijn) en `check_country`.
- [ ] Unit tests schrijven met pytest.
- [ ] De server testen met de MCP Inspector.

**Klaar als:** je in de Inspector een perceel kunt valideren en de juiste foutmelding terugkrijgt.

### Dinsdag 27 okt: orchestrator en eerste subagent

**Leren:** Claude Agent SDK (agent loop, subagents, toegestane tools) en het artikel over effectieve agents.

- [ ] Orchestrator bouwen die een zending inleest en het werk verdeelt.
- [ ] Geo-subagent die alleen geo-mcp-tools mag gebruiken (autorisatie per agent).
- [ ] Gestructureerde output met Pydantic: per perceel goedgekeurd of afgekeurd, met reden.
- [ ] Cost tracker: tokens en kosten per run en per agent loggen.
- [ ] CLI: `python -m eudr check data/zending_01.json`.

**Klaar als:** één commando een zending van begin tot eind controleert. Dit is je eerste demo.

### Woensdag 28 okt: ontbossingscheck

**Leren:** de Global Forest Watch Data API, de dataset over bosverlies en de peildatum 31 december 2020.

- [ ] forest-mcp bouwen: `check_forest_loss` geeft per perceel de hectares bosverlies na 2020.
- [ ] API-antwoorden cachen, zodat demo en evals niet van een externe API afhangen.
- [ ] Ontbossing-subagent die alleen forest-mcp-tools mag gebruiken.
- [ ] Orchestrator combineert geo- en ontbossingsresultaat tot een risicoscore per perceel.

**Klaar als:** een testperceel met bekend bosverlies als hoog risico uit de run komt.

### Donderdag 29 okt: API gateway en PII-guardrail

**Leren:** FastAPI en Presidio (analyzer, anonymizer, eigen recognizers).

- [ ] FastAPI-app met `POST /checks` en `GET /checks/{id}`, API-key-authenticatie en rate limiting.
- [ ] PII-guardrail met Presidio: namen, telefoonnummers en ID-nummers pseudonimiseren vóór elke LLM-call, ook in tool-resultaten.
- [ ] Coördinaten nooit naar het LLM sturen: agents krijgen alleen perceel-ID's en uitkomsten.
- [ ] Test die bewijst dat er geen PII in de LLM-input zit.

**Klaar als:** je via de API een check start en in de logs alleen pseudoniemen ziet.

### Vrijdag 30 okt: memory, wetgeving en review

**Leren:** Postgres met pgvector, de basis van RAG en human-in-the-loop.

- [ ] Postgres + pgvector in Docker Compose, als session store (status per check) en memory (historie per leverancier).
- [ ] regulation-mcp bouwen: `search_regulation` doorzoekt de EUDR-tekst en FAQ en geeft bij elk antwoord de bron.
- [ ] Wetgeving-subagent die de risicoklasse van het herkomstland en de relevante artikelen geeft.
- [ ] Review-stap: een check krijgt status `wacht_op_review` en wordt goedgekeurd of afgewezen via `POST /checks/{id}/approve` of `/reject`.
- [ ] DDS-concept pas genereren na goedkeuring.

**Klaar als:** een check eindigt in een goedgekeurd DDS-concept.

### Zaterdag 31 okt: evals, tracing en Docker

**Leren:** tracing met Langfuse en hoe je een eval-set opzet.

- [ ] Eval-set met 15 tot 20 testpercelen en hun verwachte uitkomst, plus een script dat de score berekent.
- [ ] Langfuse-tracing van prompts, agent calls en tool calls.
- [ ] Alles laten draaien met `docker compose up`.
- [ ] README schrijven: probleem, architectuurdiagram, quickstart, eval-score, kosten per check en een kopje "Productie-overwegingen".

**Klaar als:** iemand anders de repo kan clonen en met één commando kan draaien.

### Zondag 1 nov: buffer en lancering

- [ ] Afmaken wat is uitgelopen.
- [ ] Demo-GIF van 60 seconden opnemen: upload, agents, review, DDS.
- [ ] Repo opschonen en taggen als `v1.0`.
- [ ] Laatste LinkedIn-post plaatsen en het project op je cv zetten.

**Klaar als:** de repo openbaar is en de post live staat.

## Leeslijst

Lees per dag alleen wat in de tabel staat. Bronnen met "naslag" open je pas als je vastloopt.

| Dag | Onderwerp | Bron | Tijd |
| --- | --- | --- | --- |
| Vooraf | Hoe goede agents eruitzien | [Building effective agents (Anthropic)](https://www.anthropic.com/research/building-effective-agents) | 20 min |
| Ma | Wat MCP is | [Model Context Protocol](https://modelcontextprotocol.io) | 15 min |
| Ma | Je eerste MCP server | [FastMCP-tutorial](https://gofastmcp.com/tutorials/create-mcp-server) | 20 min |
| Ma | Officiële MCP SDK | [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk) | naslag |
| Ma | Geometrie in Python | [Shapely-documentatie](https://shapely.readthedocs.io) | naslag |
| Ma | Wat de EUDR eist | [EUDR FAQ (Europese Commissie)](https://environment.ec.europa.eu/publications/frequently-asked-questions-deforestation-regulation_en) | 30 min |
| Di | Agents bouwen | [Agent SDK overview](https://platform.claude.com/docs/en/agent-sdk/overview) | 20 min |
| Di | Python-API van de SDK | [Agent SDK Python-referentie](https://code.claude.com/docs/en/agent-sdk/python) | naslag |
| Wo | Bosverliesdata | [GFW: tree cover loss](https://data-api.globalforestwatch.org/dataset/umd_tree_cover_loss) | 15 min |
| Do | API bouwen | [FastAPI-tutorial](https://fastapi.tiangolo.com/tutorial/) | 30 min |
| Do | PII detecteren en maskeren | [Microsoft Presidio](https://microsoft.github.io/presidio/) | 30 min |
| Vr | EUDR in de praktijk | [EUDR-implementatie (Europese Commissie)](https://green-business.ec.europa.eu/deforestation-regulation-implementation_en) | 15 min |
| Vr | Vectorzoeken in Postgres | [pgvector](https://github.com/pgvector/pgvector) | 15 min |
| Za | Tracing en evals | [Langfuse-documentatie](https://langfuse.com/docs) | 20 min |

## Repo-structuur

Elke MCP server staat los, zodat je hem apart kunt testen en hergebruiken. De agentcode staat in `src/eudr`.

```text
eudr-compliance-agent/
├── README.md
├── docker-compose.yml
├── pyproject.toml
├── data/
│   ├── zendingen/           nep-zendingen (JSON)
│   └── percelen/            nep-percelen (GeoJSON)
├── mcp_servers/
│   ├── geo_mcp/
│   ├── forest_mcp/
│   └── regulation_mcp/
├── src/eudr/
│   ├── __main__.py          CLI
│   ├── agents/              orchestrator + subagents
│   ├── gateway/             FastAPI-app
│   ├── guardrails/          PII (Presidio)
│   ├── memory/              Postgres, session store
│   ├── review/              menselijke review
│   └── cost_tracker.py
├── evals/
│   ├── cases.json
│   └── run_evals.py
├── tests/
└── docs/
    ├── architectuur.png
    └── productie-overwegingen.md
```

## LinkedIn-posts

Vier posts verspreid over de week maken er een verhaal van, in plaats van één losse post aan het eind.

| Wanneer | Onderwerp | Haak |
| --- | --- | --- |
| Ma 26 okt | Aankondiging | Over twee maanden moeten koffie-importeurs bewijzen dat hun bonen niet van ontbost land komen. Ik bouw deze week een AI-agent die dat controleert. |
| Di 27 okt | Eerste demo | Screenshot van de eerste run, plus wat één check kost. |
| Do 29 okt | Ontwerpkeuze | Waarom coördinaten van boeren nooit naar het LLM gaan: het LLM beslist, code rekent. |
| Zo 1 nov | Lancering | Demo-GIF, architectuurdiagram, eval-score en de link naar de repo. |

## Risico's en noodplan

Loop je achter, schrap dan in deze volgorde. Laat de PII-guardrail, de evals en de README altijd staan: dat zijn je verkoopargumenten.

1. Wetgeving-RAG: vervang die door een vaste tabel met de risicoklasse per land.
2. Memory per leverancier: houd alleen de session store.
3. Langfuse-tracing: houd de cost tracker.
4. Rate limiting in de gateway.

Bekende valkuilen:

- **Global Forest Watch is traag of werkt niet:** download vooraf de data van één koffieregio en gebruik die als lokaal bestand. Voor de demo is dat genoeg.
- **Je loopt vast op de Agent SDK:** stap over op de gewone Messages API met tool use. De architectuur blijft hetzelfde.
- **De kosten lopen op:** gebruik een kleiner model zoals Haiku voor subagents en tests.
- **Een taak duurt twee keer zo lang als gepland:** zet hem op "later" en ga door met de volgende.

## Bronnen

- [DHL: EUDR-eisen voor exporteurs](https://www.dhl.com/discover/en-br/regulatory-affairs/eudr-export-european-union): toepassing vanaf 30 december 2026.
- [NKG: EUDR](https://www.nkg.net/eudr): due diligence-verklaring met geolocatie van alle percelen.
