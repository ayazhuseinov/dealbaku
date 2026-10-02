"""
STEP 6 - Build the client brief: a JSON report plus formatted console text.
"""

import json
from datetime import date
from pathlib import Path
from typing import Dict, List, Optional

from utils import config
from utils.helpers import slugify, tidy

RULE = "─" * 29


def _money(v) -> str:
    return "?" if v is None else f"{tidy(v):g}"


def _price_range(s: Dict) -> str:
    lo, hi = s.get("price_min"), s.get("price_max")
    if lo is None and hi is None:
        return "n/a"
    if hi is None or lo == hi:
        return f"¥{_money(lo if lo is not None else hi)}"
    return f"¥{_money(lo)}-{_money(hi)}"


def _supplier_entry(s: Dict, rank: int) -> Dict:
    return {
        "rank": rank,
        "supplier_id": s.get("supplier_id"),
        "supplier_name": s.get("company_name_en"),
        "supplier_name_cn": s.get("company_name_cn"),
        "score": tidy(s.get("score"), 1),
        "percentiles": s.get("percentiles"),
        "platform_badge": s.get("platform_badge"),
        "years": s.get("years_in_business"),
        "rating": s.get("customer_feedback_rating"),
        "reviews": s.get("review_count"),
        "price_range": _price_range(s),
        "moq_range": f"{s.get('moq_min')}-{s.get('moq_max')}",
        "avg_shipping_days": s.get("avg_shipping_days"),
        "location": s.get("location"),
        "store_link": s.get("store_link"),
        "wechat": s.get("wechat_contact"),
        "phone": s.get("phone_number"),
        "email": s.get("email"),
        "business_registration_status": s.get("business_registration_status"),
        "glm_analysis": s.get("glm_analysis"),
    }


def _dist_block(m: Dict) -> Dict:
    return {k: m[k] for k in ("min", "max", "median", "top_quartile_threshold")}


def build_json_report(top_5: List[Dict], distribution: Dict, total_found: int, *,
                      context: Dict, top_10: Optional[List[Dict]] = None,
                      all_suppliers: Optional[List[Dict]] = None) -> Dict:
    pricing = {k: v for k, v in distribution["market_pricing"].items() if k != "data_points"}
    report = {
        "product": context["product"],
        "location_constraint": context["location"],
        "moq_constraint": context["moq"],
        "platform_constraint": context["platform"],
        "search_date": context["search_date"],
        "data_source": context.get("data_source", "1688 API"),
        "total_suppliers_found": total_found,
        "suppliers_meeting_constraints": distribution["supplier_count"],
        "distribution": {
            "years_in_business": _dist_block(distribution["years_in_business"]),
            "feedback_rating": _dist_block(distribution["feedback_rating"]),
            "review_count": _dist_block(distribution["review_count"]),
            "market_pricing": pricing,
        },
        "top_5_suppliers": [_supplier_entry(s, i) for i, s in enumerate(top_5, 1)],
    }
    if top_10 is not None:
        report["top_10_ranked"] = [
            {"rank": i, "supplier_id": s.get("supplier_id"),
             "supplier_name": s.get("company_name_en"), "score": tidy(s.get("score"), 1)}
            for i, s in enumerate(top_10, 1)
        ]
    if all_suppliers is not None:
        report["all_suppliers"] = all_suppliers
    return report


def _range_line(label: str, m: Dict, unit: str) -> str:
    if m["min"] is None:
        return f"{label}: n/a"
    return f"{label}: {m['min']:g}–{m['max']:g} {unit} (median: {m['median']:g} {unit})"


def _glm_lines(analysis: Optional[Dict]) -> List[str]:
    if not analysis:
        return ["GLM Analysis: not run"]
    if "error" in analysis:
        return [f"GLM Analysis: unavailable ({analysis['error']})"]
    rec = str(analysis.get("recommendation", "")).replace("_", " ").upper()
    return [
        "GLM Analysis:",
        f"  Quality: {analysis.get('quality_confidence', '?')}/10 | "
        f"Reliability: {analysis.get('supply_reliability', '?')}/10",
        f"  Strength: \"{analysis.get('key_strength', '')}\"",
        f"  Risk: \"{analysis.get('main_risk', '')}\"",
        f"  Leverage: \"{analysis.get('negotiation_leverage', '')}\"",
        f"  → Recommendation: {rec}",
    ]


def format_console_report(report: Dict) -> str:
    d = report["distribution"]
    p = d["market_pricing"]
    platform_label = config.PLATFORM_LABELS.get(report["platform_constraint"],
                                                report["platform_constraint"])
    lines = [
        "",
        "═" * 60,
        f"SUPPLIER DISCOVERY REPORT — {report['product'].title()}",
        f"Location: {report['location_constraint']} | MOQ Limit: {report['moq_constraint']} units"
        f" | Platform: {platform_label}",
        f"Search Date: {report['search_date']}",
        "",
        "MARKET OVERVIEW",
        RULE,
        f"Total suppliers found: {report['total_suppliers_found']}",
        f"Suppliers meeting all constraints: {report['suppliers_meeting_constraints']}",
        "Distribution Analysis:",
        "  " + _range_line("Years in Business", d["years_in_business"], "years"),
        "  " + _range_line("Feedback Rating", d["feedback_rating"], "stars"),
        "  " + _range_line("Review Count", d["review_count"], "reviews"),
    ]
    if p["min_price"] is not None:
        lines.append(f"  Market Price: ¥{_money(p['min_price'])}–{_money(p['max_price'])} per unit "
                     f"(average: ¥{p['average_price']:.2f})")
    else:
        lines.append("  Market Price: n/a")
    lines += ["", f"TOP {len(report['top_5_suppliers'])} SUPPLIERS", RULE]

    for s in report["top_5_suppliers"]:
        name = s["supplier_name"]
        if s.get("supplier_name_cn") and s["supplier_name_cn"] != name:
            name = f"{name} ({s['supplier_name_cn']})"
        lines += [
            f"#{s['rank']} {name} | Score: {s['score']:g}/100",
            f"  Location: {s['location']}",
            f"  Years: {s['years']} | Rating: {s['rating']} | Reviews: {s['reviews']}"
            f" | Badge: {s['platform_badge']}",
            f"  Price: {s['price_range']} | MOQ: {s['moq_range']} units",
            f"  Contact: WeChat: {s['wechat']} | Phone: {s['phone']} | Email: {s['email']}",
            f"  Store: {s['store_link']}",
            *("  " + line for line in _glm_lines(s["glm_analysis"])),
            "",
        ]
    lines += [
        "NEXT STEPS",
        RULE,
        "1. Contact top 3 suppliers via WeChat or phone",
        "2. Request product catalog and detailed pricing",
        "3. Negotiate sample order and payment terms",
        "4. Verify business registration via Qichacha (企查查)",
        "═" * 60,
    ]
    return "\n".join(lines)


def report_basename(product: str, search_date: str) -> str:
    return f"dealbaku_supplier_analysis_{slugify(product)}_{search_date}"


def generate_report(top_5: List[Dict], distribution: Dict, total_found: int, *,
                    context: Dict, top_10: Optional[List[Dict]] = None,
                    all_suppliers: Optional[List[Dict]] = None,
                    output_dir: str = ".") -> Dict:
    """
    Print the console brief and save `<name>.json` + `<name>.txt`.
    `context` holds product, location, moq, platform and (optionally) search_date.
    Returns {"report": dict, "text": str, "json_path": Path, "text_path": Path}.
    """
    context = dict(context)
    context.setdefault("search_date", date.today().isoformat())
    report = build_json_report(top_5, distribution, total_found, context=context,
                               top_10=top_10, all_suppliers=all_suppliers)
    text = format_console_report(report)

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    base = report_basename(context["product"], context["search_date"])
    json_path, text_path = out / f"{base}.json", out / f"{base}.txt"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    text_path.write_text(text + "\n", encoding="utf-8")

    print(text)
    print(f"\nReport saved: {json_path}")
    return {"report": report, "text": text, "json_path": json_path, "text_path": text_path}
