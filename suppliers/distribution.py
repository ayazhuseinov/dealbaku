"""
STEP 2 - Analyse how the matching suppliers are distributed.

Nothing here applies a fixed cut-off. The 75th percentile of each metric is
computed from whatever the search returned, so "top quartile" means "better
than three quarters of *this* market", whether that is 4 years or 14.
"""

from typing import Dict, List

from utils.helpers import describe, tidy


def _metric(suppliers: List[Dict], field: str) -> Dict:
    values = [s.get(field) for s in suppliers]
    stats = describe(values)
    threshold = stats["top_quartile_threshold"]
    top_count = 0
    if threshold is not None:
        top_count = sum(1 for v in values if v is not None and v >= threshold)
    return {
        "min": tidy(stats["min"]),
        "max": tidy(stats["max"]),
        "median": tidy(stats["median"]),
        "mean": tidy(stats["mean"]),
        "top_quartile_threshold": tidy(stats["top_quartile_threshold"]),
        "top_quartile_count": top_count,
        "data_points": stats["count"],
    }


def _pricing(suppliers: List[Dict]) -> Dict:
    # Market price is read off each supplier's entry price (price_min).
    stats = describe(s.get("price_min") for s in suppliers)
    return {
        "min_price": tidy(stats["min"]),
        "max_price": tidy(stats["max"]),
        "average_price": tidy(stats["mean"]),
        "median_price": tidy(stats["median"]),
        "data_points": stats["count"],
    }


def analyze_distribution(suppliers: List[Dict]) -> Dict:
    """Return min/max/median/top-quartile per metric plus market pricing."""
    return {
        "supplier_count": len(suppliers),
        "years_in_business": _metric(suppliers, "years_in_business"),
        "feedback_rating": _metric(suppliers, "customer_feedback_rating"),
        "review_count": _metric(suppliers, "review_count"),
        "market_pricing": _pricing(suppliers),
    }


def _fmt(value, unit: str = "") -> str:
    if value is None:
        return "n/a"
    text = f"{value:g}" if isinstance(value, (int, float)) else str(value)
    return f"{text}{unit}"


def _plural(value, singular: str, plural: str) -> str:
    return f" {singular}" if value == 1 else f" {plural}"


def format_distribution(dist: Dict) -> str:
    """Detailed blocks, one per metric (printed after STEP 2)."""
    n = dist["supplier_count"]
    blocks = []
    for key, title, sing, plur in (
        ("years_in_business", "Years in business", "year", "years"),
        ("feedback_rating", "Feedback rating", "star", "stars"),
        ("review_count", "Review count", "review", "reviews"),
    ):
        m = dist[key]
        u = lambda v: _fmt(v, _plural(v, sing, plur)) if v is not None else "n/a"  # noqa: E731
        blocks.append("\n".join([
            f"{title} distribution:",
            f"  * Min: {u(m['min'])}",
            f"  * Max: {u(m['max'])}",
            f"  * Median: {u(m['median'])}",
            f"  * Top quartile (75th percentile): ≥{u(m['top_quartile_threshold'])}",
            f"  * Top quartile suppliers: {m['top_quartile_count']} out of {n}",
        ]))
    p = dist["market_pricing"]
    money = lambda v: f"¥{v:.2f}".replace(".00", "") if v is not None else "n/a"  # noqa: E731
    blocks.append("\n".join([
        "Market pricing distribution:",
        f"  * Minimum: {money(p['min_price'])} per unit",
        f"  * Maximum: {money(p['max_price'])} per unit",
        f"  * Average: ¥{p['average_price']:.2f} per unit" if p["average_price"] is not None
        else "  * Average: n/a",
        f"  * Median: {money(p['median_price'])} per unit",
    ]))
    return "\n\n".join(blocks)
