# EUDR and coffee: the problem we're solving

Oct 26, 2026 · @hassan

## In short

From 30 December 2026, a company that brings coffee onto the EU market must prove two things: the coffee grew on land that was not deforested after 31 December 2020, and it was produced legally. The proof is a due diligence statement that includes the location of every plot of land the coffee came from.

For coffee this is hard. One container can hold beans from hundreds of small farms that passed through several middlemen, so the data arrives incomplete, messy and full of farmers' personal details. Our agent checks that data, flags the risky plots and drafts the statement for a human to approve.

## Why the law exists

Forests are mostly cut down to make room for farming, and Europe buys a big share of what grows there. According to the Commission, [about 80% of global deforestation is driven by agricultural expansion](https://www.feednavigator.com/Article/2020/02/07/How-to-minimize-EU-contribution-to-deforestation). A study it funded found that [EU consumption accounted for about 10% of global embodied deforestation](https://pure.iiasa.ac.at/id/eprint/14868/1/1.%20Report%20analysis%20of%20impact.pdf), almost entirely through imports.

This matters for the climate too: [deforestation causes about 10% of global greenhouse gas emissions](https://www.canberratimes.com.au/story/8349415/coffee-firms-not-ready-to-comply-with-eu-law-report/). So the EU decided that companies selling seven commodities in Europe must prove their products are not linked to it: cattle, cocoa, coffee, oil palm, rubber, soy and wood.

## What the law requires

Before coffee enters the EU, the importer files a due diligence statement in the Commission's information system. To do that, it needs [five pieces of data per batch](https://dcycle.io/eudr/), and almost all of them sit with its suppliers.

| Data point | What it is | What our agent does with it |
| --- | --- | --- |
| HS code and quantity | The product type and how much | Reads it from the shipment file |
| Plot geolocation | A GPS point per plot, or a polygon when the plot is larger than 4 ha | geo-mcp validates it |
| Country | Where the coffee grew | Looks up the country's risk class |
| Production date or period | When it was harvested | Checks it against the cut-off date |
| Proof of legality | Evidence it was produced under local law (land, labour, tax) | Checks it is there and flags gaps |

The statement is the end of a three-step process: gather the information, assess the risk, and reduce any risk that isn't negligible. Without negligible risk, the coffee cannot enter.

**Risk depends on the country.** The Commission sorted every country into three classes. The class decides how deep the due diligence goes and how often authorities check ([source](https://www.european-rubber-journal.com/article/2097547/european-commission-publishes-country-benchmarking-for-eudr)).

| Class | Countries | Authorities check | Due diligence |
| --- | --- | --- | --- |
| High | 4: Belarus, Myanmar, North Korea, Russia | 9% of operators | Full, with enhanced checks |
| Standard | About 50, including Brazil and Indonesia | 3% | Full: information, assessment, mitigation |
| Low | About 140 others | 1% | Information and statement only, unless there are warning signs |

Low risk is not an exemption: geolocation, proof of legality and the statement are still required.

**Who does what.** The company that first places coffee on the EU market (usually the importer) is the operator: it does the full due diligence and files the statement. A roaster that buys already-declared coffee is a downstream operator: it keeps and passes on the statement's reference number.

**Dates and penalties.** Medium and large companies must comply from 30 December 2026, micro and small ones from 30 June 2027, and instant coffee joins from 30 December 2027. Breaking the rules means a fine of at least 4% of annual EU turnover, confiscation of the goods and the revenue from them, and exclusion from public contracts. Records must be kept for five years ([source](https://dcycle.io/eudr/)).

## Why coffee is hard

&#91;embedded content: coffee supply chain · 5 hand-offs, where our agent sits\]

Coffee grows on [12.5 million farms, 84% of them smaller than two hectares](https://sca.coffee/sca-news/25/issue-22/cracking-coffee-regulation), often remote and on hilly ground. Beans from many farms are pooled early, and [most coffee passes through several actors](https://unctad.org/system/files/non-official-document/unctad_gcf_s3_gerardo_patacconi.pdf) before it is exported. Mapping farms is slow fieldwork: at one large trader, [field staff manage only three or four farms a day](https://www.foodnavigator.com/Article/2025/08/29/coffee-key-traceability-challenges-amid-eudr/).

The human risk: importers may [shift to origins with better traceability](https://www.canberratimes.com.au/story/8349415/coffee-firms-not-ready-to-comply-with-eu-law-report/) like Brazil, and drop millions of small farmers. Tools that make compliance cheaper help keep those farmers in the market.

## What importers do today and where it hurts

Today most of this runs on email and spreadsheets, and the slowest step is getting the data from suppliers.

- **Collecting the data:** importers send [hundreds of emails with a different spreadsheet per supplier](https://dcycle.io/eudr/), and suppliers at origin get a different format from every European customer. Replies take weeks, or never come.
- **Scale:** the EU imports [about 150,000 containers of green coffee a year](https://sca.coffee/sca-news/25/issue-22/cracking-coffee-regulation), each needing traceable plots behind it.
- **Certificates don't cover it:** a sustainability certificate supports the risk assessment, but [does not replace geolocation or the statement](https://dcycle.io/eudr/).
- **Judgment calls:** satellite data shows tree cover loss, not its cause, so someone has to decide whether a signal means deforestation or something harmless like replanting.
- **Personal data:** a farmer's name linked to the coordinates of their plot is personal data under GDPR, so it needs careful handling across the whole chain.

## Where our agent fits

Our agent works for the importer's compliance officer. It takes the messy supplier data that arrives with a shipment, checks it, and hands back a draft statement plus a list of what needs a human decision.

| Step | The agent | The human |
| --- | --- | --- |
| Check the geodata | Validates every point and polygon with code, including the 4 ha rule | Fixes data with the supplier |
| Check for deforestation | Measures tree cover loss after 2020 per plot and flags signals | Decides on ambiguous cases |
| Check country and legality | Looks up the risk class and checks the proof is present | Judges whether the proof is good enough |
| Draft the statement | Writes the draft with its reasoning and sources | Approves or rejects it |
| File the statement | Not in scope | Submits it in the EU information system |

Why an agent and not a plain script: supplier data comes in many formats, satellite signals need interpretation, and every decision needs a written explanation an inspector can follow. The calculations stay in code; the agent does the reading, combining and explaining.

Out of scope on purpose: collecting data from farmers, mapping plots in the field, and filing the statement for real.

## Glossary

| Term | Meaning |
| --- | --- |
| EUDR | EU Deforestation Regulation, Regulation (EU) 2023/1115 |
| Operator | The company that first places the product on the EU market or exports it; files the statement |
| Downstream operator | A company further down the chain, like a roaster; keeps and passes on the statement's reference number |
| Trader | A company that only distributes the product; has documentation duties |
| DDS | Due diligence statement: the declaration filed before the product enters the market |
| Cut-off date | 31 December 2020; land deforested after this date makes the product non-compliant |
| Geolocation | The location of a plot: a point, or a polygon for plots larger than 4 ha |
| Polygon | A closed shape of coordinates that outlines a plot's border |
| Negligible risk | The level of risk the due diligence must reach before the product may enter |
| Country benchmarking | The Commission's split of countries into low, standard and high risk |
| HS code | The customs code that says which product it is |
| Tree cover loss | Satellite-measured loss of trees in a pixel; not the same as deforestation |
| Smallholder | A small family farm; most coffee farms are smallholdings |

## Sources

- [Dcycle: EUDR scope, roles and obligations in 2026](https://dcycle.io/eudr/)
- [European Rubber Journal: Commission publishes country benchmarking](https://www.european-rubber-journal.com/article/2097547/european-commission-publishes-country-benchmarking-for-eudr)
- [CMS: the EUDR benchmarking list](https://cms.law/en/int/publication/european-union-deforestation-regulation/the-eudr-benchmarking-list-is-here-and-comes-as-a-surprise)
- [SCA: coffee supply chain challenges with EUDR compliance](https://sca.coffee/sca-news/25/issue-22/cracking-coffee-regulation)
- [ICO presentation at UNCTAD: EUDR and coffee traceability](https://unctad.org/system/files/non-official-document/unctad_gcf_s3_gerardo_patacconi.pdf)
- [FoodNavigator: 5 traceability challenges for coffee](https://www.foodnavigator.com/Article/2025/08/29/coffee-key-traceability-challenges-amid-eudr/)
- [Canberra Times: coffee firms not ready for EU law](https://www.canberratimes.com.au/story/8349415/coffee-firms-not-ready-to-comply-with-eu-law-report/)
- [Commission-funded study: impact of EU consumption on deforestation](https://pure.iiasa.ac.at/id/eprint/14868/1/1.%20Report%20analysis%20of%20impact.pdf)
- [FeedNavigator: how to minimize EU contribution to deforestation](https://www.feednavigator.com/Article/2020/02/07/How-to-minimize-EU-contribution-to-deforestation)
- [GFW: tree cover loss dataset](https://data-api.globalforestwatch.org/dataset/umd_tree_cover_loss)
