"""Score a computed value against the published measurement."""

from __future__ import annotations


def score_row(computed: float, measured: float, reference_uncertainty_pct: float | None) -> dict:
    delta = computed - measured
    if measured == 0:
        error_pct = None
    else:
        error_pct = abs(delta) / abs(measured) * 100.0
    if reference_uncertainty_pct is None or reference_uncertainty_pct <= 0 or error_pct is None:
        return {
            "delta": delta,
            "error_pct": error_pct,
            "z": None,
            "inside_bar": False,
            "bar": "missing",
        }
    z = error_pct / reference_uncertainty_pct
    return {
        "delta": delta,
        "error_pct": error_pct,
        "z": z,
        "inside_bar": z <= 1.0,
        "bar": "published",
    }


def kill_metric(score: dict | None) -> dict:
    """Kill a proposal that is outside the published uncertainty.

    The published bar is the only pass. z > 1 is a kill. A missing bar
    cannot show that the value sits inside a published uncertainty, so it
    is a kill too. Flat percent is reported on the score and is not a
    second cutoff. Inside the bar is consistency with that measurement.
    It is not sent and it is not a promotion.
    """
    if not score:
        reason = "unscored"
    elif score.get("bar") != "published" or score.get("z") is None:
        reason = "no_published_uncertainty"
    elif float(score["z"]) > 1.0:
        reason = "outside_published_uncertainty"
    else:
        reason = "inside_published_uncertainty"
    return {"killed": reason != "inside_published_uncertainty", "reason": reason, "send": False}
