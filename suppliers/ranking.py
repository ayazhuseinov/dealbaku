"""
STEP 3 - Rank suppliers by their position within the observed distribution.

Each metric is scored as (value - min) / (max - min) * 100 against the
suppliers actually found, then weighted:

    score = years*0.25 + rating*0.35 + reviews*0.25 + badge bonus (gold 10, verified 5)
"""

from typing import Dict, List, Optional

from utils import config
from utils.helpers import percentile_score


def score_supplier(supplier: Dict, dist: Dict) -> Dict:
    years, rating, reviews = (dist["years_in_business"], dist["feedback_rating"],
                              dist["review_count"])
    pctl = {
        "years": percentile_score(supplier.get("years_in_business"), years["min"], years["max"]),
        "rating": percentile_score(supplier.get("customer_feedback_rating"),
                                   rating["min"], rating["max"]),
        "reviews": percentile_score(supplier.get("review_count"),
                                    reviews["min"], reviews["max"]),
    }
    bonus = config.BADGE_BONUS.get(supplier.get("platform_badge"), 0)
    score = (pctl["years"] * config.WEIGHT_YEARS
             + pctl["rating"] * config.WEIGHT_RATING
             + pctl["reviews"] * config.WEIGHT_REVIEWS
             + bonus)
    return {
        "percentiles": {k: round(v, 1) for k, v in pctl.items()},
        "badge_bonus": bonus,
        "score": round(score, 1),
    }


def _sort_key(s: Dict):
    # Score first; ties broken by rating, then reviews, then years.
    return (s["score"], s.get("customer_feedback_rating") or 0,
            s.get("review_count") or 0, s.get("years_in_business") or 0)


def rank_suppliers_by_percentile(suppliers: List[Dict], distribution: Dict,
                                 limit: Optional[int] = config.TOP_RANKED) -> List[Dict]:
    """
    Score every supplier (in place, so the full list carries scores too),
    sort by score DESC and return the top `limit` (None = all).
    """
    for s in suppliers:
        s.update(score_supplier(s, distribution))
    ranked = sorted(suppliers, key=_sort_key, reverse=True)
    for i, s in enumerate(ranked, 1):
        s["rank"] = i
    return ranked if limit is None else ranked[:limit]
