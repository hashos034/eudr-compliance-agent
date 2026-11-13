"""Turn a plot's cached loss per year into a forest loss result.

Nothing in here knows about MCP, LLMs or coordinates, so it is easy to unit test.
"""

# EUDR cut-off: land deforested after 31 December 2020 makes a product non-compliant.
# The data gives only a year per pixel, so 2020 counts as before the cut-off.
CUTOFF_YEAR = 2020

# About two 30 m pixels. A single pixel on its own is often satellite noise.
MIN_FLAG_HA = 0.15


def assess(plot_id: str, record: dict | None) -> dict:
    """Summarize one cache record. No record means unknown, never "no loss"."""
    if record is None:
        return {
            "plot_id": plot_id,
            "status": "no_data",
            "flagged": None,
            "note": "No forest data for this plot's current geometry, so forest loss is unknown.",
        }
    if record["status"] == "not_checked":
        return {
            "plot_id": plot_id,
            "status": "not_checked",
            "flagged": None,
            "note": "The plot's geometry is invalid, so forest loss could not be measured.",
        }

    by_year = {int(year): ha for year, ha in record["loss_ha_by_year"].items()}
    after = {year: ha for year, ha in sorted(by_year.items()) if year > CUTOFF_YEAR}
    loss_after = sum(after.values())
    loss_before = sum(ha for year, ha in by_year.items() if year <= CUTOFF_YEAR)
    return {
        "plot_id": plot_id,
        "status": "checked",
        "flagged": loss_after >= MIN_FLAG_HA,
        "loss_after_cutoff_ha": round(loss_after, 2),
        "loss_after_cutoff_pct": round(100 * loss_after / record["measured_area_ha"], 1),
        "loss_after_cutoff_by_year": {str(year): round(ha, 2) for year, ha in after.items()},
        "loss_up_to_cutoff_ha": round(loss_before, 2),
        "note": "Tree cover loss is a satellite signal. It does not show why the trees were lost.",
    }
