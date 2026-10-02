"""
STEP 1 - Search 1688 with hard constraints.

1688 search results are *offers* (product listings), not suppliers, so the
pipeline is: fetch every result page -> normalise each record -> merge offers
from the same seller into one supplier -> apply hard constraints (location,
MOQ, platform badge) -> number survivors SUP-0001, SUP-0002, ...

The HTTP client targets a 1688 data gateway (default: OneBound item_search,
override with ALIBABA_1688_API_URL). Field names differ between gateways, so
normalise_record() looks for each field under several common names, English
and Chinese. The same normaliser is used for the manual-fallback file, so a
JSON/CSV export from any source goes through identical constraint checks.
"""

import csv
import json
import logging
from pathlib import Path
from typing import Dict, Iterable, List, Optional

import requests

from utils import config
from utils.helpers import location_matches, parse_range, to_float, to_int, years_in_business

logger = logging.getLogger(__name__)


class SearchAPIError(ValueError):
    """The 1688 API could not be reached or returned an error."""


class NoSuppliersFound(ValueError):
    """Search worked, but nothing survived the hard constraints."""


class SupplierList(list):
    """A list of suppliers that also remembers how many were seen before filtering."""

    def __init__(self, items: Iterable[Dict] = (), total_found: int = 0,
                 excluded: Optional[Dict[str, int]] = None):
        super().__init__(items)
        self.total_found = total_found
        self.excluded = excluded or {}


# ---------------------------------------------------------------------------
# Field lookup
# ---------------------------------------------------------------------------

FIELD_CANDIDATES = {
    "seller_id": ["seller_id", "sellerId", "member_id", "memberId", "user_id", "userId",
                  "shop_id", "shopId", "login_id", "loginId", "seller_nick", "nick"],
    "company_name_cn": ["company_name_cn", "companyNameCn", "company_name", "companyName",
                        "company", "seller_company", "shop_name", "shopName", "store_name",
                        "seller_nick", "nick", "公司名称", "店铺名称"],
    "company_name_en": ["company_name_en", "companyNameEn", "company_en", "english_name",
                        "name_en"],
    "store_link": ["store_link", "store_url", "storeUrl", "shop_url", "shopUrl", "shop_link",
                   "seller_url", "company_url", "winport_url", "店铺链接"],
    "offer_link": ["detail_url", "detailUrl", "offer_url", "offerUrl", "item_url", "url"],
    "badge": ["platform_badge", "badge", "member_type", "memberType", "seller_type",
              "shop_type", "tp_type", "会员类型"],
    "years": ["years_in_business", "years", "tp_year", "tpYear", "tp_years", "shop_years",
              "joined", "join_year", "joined_year", "member_since", "start_year",
              "入驻年限", "诚信通年限"],
    "province": ["province", "省份"],
    "city": ["city", "城市"],
    "location": ["location", "seller_location", "area", "address", "region", "所在地"],
    "rating": ["customer_feedback_rating", "rating", "feedback_rating", "shop_score",
               "composite_score", "compositeScore", "score", "star", "综合服务分", "评分"],
    "review_count": ["review_count", "reviews", "reviewCount", "comment_count",
                     "commentCount", "rate_count", "evaluate_count", "feedback_count",
                     "评价数"],
    "moq_min": ["moq_min", "moq", "min_order", "minOrder", "min_order_quantity",
                "minOrderQuantity", "quantity_begin", "quantityBegin", "begin_amount",
                "起订量"],
    "moq_max": ["moq_max"],
    "price_min": ["price_min", "priceMin", "min_price", "promotion_price", "price",
                  "price_range", "priceRange", "价格"],
    "price_max": ["price_max", "priceMax", "max_price", "price_range", "priceRange", "price"],
    "shipping_days": ["avg_shipping_days", "shipping_days", "delivery_days", "lead_time",
                      "send_goods_days", "发货天数"],
    "wechat": ["wechat_contact", "wechat", "weixin", "wechat_id", "微信"],
    "phone": ["phone_number", "phone", "mobile", "mobile_phone", "tel", "telephone", "电话",
              "手机"],
    "email": ["email", "e_mail", "mail", "邮箱"],
    "registration": ["business_registration_status", "registration_status", "is_verified",
                     "license_verified", "is_authenticated", "工商认证"],
}

GOLD_FLAGS = ["is_gold", "isGold", "gold_supplier", "is_tp", "isTp", "is_trust_pass",
              "is_super_factory", "isSuperFactory", "is_power_merchant"]
VERIFIED_FLAGS = ["is_verified", "verified", "is_factory_verified", "factory_inspection",
                  "is_authenticated"]

GOLD_WORDS = ("gold", "诚信通", "实力商家", "超级工厂", "trustpass")
VERIFIED_WORDS = ("verified", "认证", "验厂", "验商", "audited")


def _first(raw: Dict, field: str):
    for key in FIELD_CANDIDATES[field]:
        value = raw.get(key)
        if value not in (None, "", [], {}):
            return value
    return None


def _truthy(value) -> bool:
    if isinstance(value, str):
        return value.strip().lower() in ("1", "true", "yes", "y", "是")
    return bool(value)


def _badge(raw: Dict) -> str:
    if any(_truthy(raw.get(k)) for k in GOLD_FLAGS):
        return "gold"
    text = str(_first(raw, "badge") or "").lower()
    if any(w in text for w in GOLD_WORDS):
        return "gold"
    if any(w in text for w in VERIFIED_WORDS):
        return "verified"
    if any(_truthy(raw.get(k)) for k in VERIFIED_FLAGS):
        return "verified"
    return "regular"


def _rating(raw: Dict) -> Optional[float]:
    value = to_float(_first(raw, "rating"))
    if value is None:
        return None
    # Some gateways report 0-10 or 0-100; bring everything to 0-5.
    if value > 10:
        value = value / 20
    elif value > 5:
        value = value / 2
    return round(min(max(value, 0.0), 5.0), 2)


def _location(raw: Dict) -> Optional[str]:
    city, province = _first(raw, "city"), _first(raw, "province")
    if city or province:
        parts = [str(p).strip() for p in (city, province) if p]
        return ", ".join(dict.fromkeys(parts))
    loc = _first(raw, "location")
    return str(loc).strip() if loc else None


def _registration(raw: Dict, badge: str) -> str:
    value = _first(raw, "registration")
    if isinstance(value, str) and value.strip().lower() in ("verified", "unverified"):
        return value.strip().lower()
    if value is not None:
        return "verified" if _truthy(value) else "unverified"
    # 诚信通 (gold) membership requires business-licence verification on 1688.
    return "verified" if badge in ("gold", "verified") else "unverified"


def _clean_text(value) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def normalise_record(raw: Dict) -> Dict:
    """Map one raw offer/supplier record to the canonical supplier schema."""
    badge = _badge(raw)

    price_lo, price_hi = parse_range(_first(raw, "price_min"))
    explicit_hi = to_float(raw.get("price_max") or raw.get("priceMax") or raw.get("max_price"))
    if explicit_hi is not None:
        price_hi = explicit_hi
    if price_hi is None:
        price_hi = price_lo

    moq_lo, moq_hi = parse_range(_first(raw, "moq_min"))
    explicit_moq_hi = to_float(_first(raw, "moq_max"))
    if explicit_moq_hi is not None:
        moq_hi = explicit_moq_hi

    shipping = to_float(_first(raw, "shipping_days"))
    company_cn = _clean_text(_first(raw, "company_name_cn"))

    return {
        "seller_key": str(_first(raw, "seller_id") or _first(raw, "store_link")
                          or company_cn or id(raw)),
        "company_name_cn": company_cn,
        "company_name_en": _clean_text(_first(raw, "company_name_en")),
        "store_link": _clean_text(_first(raw, "store_link")),
        "offer_link": _clean_text(_first(raw, "offer_link")),
        "platform": "1688",
        "platform_badge": badge,
        "years_in_business": years_in_business(_first(raw, "years")),
        "location": _location(raw),
        "customer_feedback_rating": _rating(raw),
        "review_count": to_int(_first(raw, "review_count")),
        "moq_min": int(moq_lo) if moq_lo is not None else None,
        "moq_max": int(moq_hi) if moq_hi is not None else None,
        "price_min": price_lo,
        "price_max": price_hi,
        "avg_shipping_days": shipping if shipping is not None else "unknown",
        "wechat_contact": _clean_text(_first(raw, "wechat")),
        "phone_number": _clean_text(_first(raw, "phone")),
        "email": _clean_text(_first(raw, "email")),
        "business_registration_status": _registration(raw, badge),
    }


def _min(a, b):
    vals = [v for v in (a, b) if v is not None]
    return min(vals) if vals else None


def _max(a, b):
    vals = [v for v in (a, b) if v is not None]
    return max(vals) if vals else None


def group_by_supplier(records: List[Dict]) -> List[Dict]:
    """Merge offers from the same seller: widen price/MOQ ranges, fill gaps."""
    merged: Dict[str, Dict] = {}
    for rec in records:
        key = rec["seller_key"]
        if key not in merged:
            merged[key] = dict(rec, offer_count=1)
            continue
        cur = merged[key]
        cur["offer_count"] += 1
        cur["price_min"] = _min(cur["price_min"], rec["price_min"])
        cur["price_max"] = _max(cur["price_max"], rec["price_max"])
        cur["moq_min"] = _min(cur["moq_min"], rec["moq_min"])
        cur["moq_max"] = _max(cur["moq_max"], rec["moq_max"])
        cur["review_count"] = _max(cur["review_count"], rec["review_count"])
        for field, value in rec.items():
            if cur.get(field) in (None, "unknown") and value not in (None, "unknown"):
                cur[field] = value
        if rec["platform_badge"] == "gold" or (
                rec["platform_badge"] == "verified" and cur["platform_badge"] == "regular"):
            cur["platform_badge"] = rec["platform_badge"]
    return list(merged.values())


# ---------------------------------------------------------------------------
# Hard constraints
# ---------------------------------------------------------------------------

def _passes_platform(badge: str, platform_req: str) -> bool:
    if platform_req == config.PLATFORM_GOLD:
        return badge == "gold"
    if platform_req == config.PLATFORM_VERIFIED:
        # Gold (诚信通) members are verified too, so they qualify.
        return badge in ("gold", "verified")
    return True


def apply_constraints(suppliers: List[Dict], location: str, moq_max: int,
                      platform_req: str) -> SupplierList:
    """
    Keep suppliers that are in `location`, can sell at or below `moq_max`
    units, and hold the required badge. A supplier with no published MOQ is
    excluded: the constraint cannot be confirmed.
    """
    platform_req = config.normalize_platform_req(platform_req)
    excluded = {"location": 0, "moq": 0, "platform": 0}
    kept = []
    for s in suppliers:
        if not location_matches(s.get("location"), location):
            excluded["location"] += 1
        elif s.get("moq_min") is None or s["moq_min"] > moq_max:
            excluded["moq"] += 1
        elif not _passes_platform(s.get("platform_badge", "regular"), platform_req):
            excluded["platform"] += 1
        else:
            kept.append(s)

    for i, s in enumerate(kept, 1):
        s["supplier_id"] = f"SUP-{i:04d}"
        if not s.get("company_name_en"):
            s["company_name_en"] = s.get("company_name_cn")
    ordered = [_ordered(s) for s in kept]
    return SupplierList(ordered, total_found=len(suppliers), excluded=excluded)


OUTPUT_FIELDS = [
    "supplier_id", "company_name_cn", "company_name_en", "store_link", "platform",
    "platform_badge", "years_in_business", "location", "customer_feedback_rating",
    "review_count", "moq_min", "moq_max", "price_min", "price_max", "avg_shipping_days",
    "wechat_contact", "phone_number", "email", "business_registration_status",
]


def _ordered(s: Dict) -> Dict:
    out = {f: s.get(f) for f in OUTPUT_FIELDS}
    out["offer_link"] = s.get("offer_link")
    out["offer_count"] = s.get("offer_count", 1)
    return out


# ---------------------------------------------------------------------------
# 1688 API client
# ---------------------------------------------------------------------------

def _extract_items(payload) -> List[Dict]:
    """Find the result list in the common gateway response shapes."""
    if isinstance(payload, list):
        return [p for p in payload if isinstance(p, dict)]
    if not isinstance(payload, dict):
        return []
    for path in (("items", "item"), ("items",), ("data", "items"), ("data", "list"),
                 ("data", "offers"), ("data",), ("result", "result"), ("result", "items"),
                 ("result",), ("offers",), ("suppliers",), ("list",)):
        node = payload
        for key in path:
            node = node.get(key) if isinstance(node, dict) else None
        if isinstance(node, list):
            return [p for p in node if isinstance(p, dict)]
    return []


def _api_error(payload) -> Optional[str]:
    if not isinstance(payload, dict):
        return None
    code = payload.get("error_code", payload.get("code"))
    if code not in (None, "", 0, "0", "0000", 200, "200", "success"):
        return f"{code}: {payload.get('error') or payload.get('message') or payload.get('msg')}"
    if payload.get("success") is False:
        return str(payload.get("message") or payload.get("msg") or "request failed")
    return None


def fetch_1688_offers(category: str, api_key: str, *, session=None,
                      max_pages: int = config.MAX_SEARCH_PAGES) -> List[Dict]:
    """Walk every result page until the API runs dry (or max_pages)."""
    if not api_key:
        raise SearchAPIError("No 1688 API key provided (--1688-key or ALIBABA_1688_API_KEY).")

    http = session or requests.Session()
    items: List[Dict] = []
    for page in range(1, max_pages + 1):
        params = {"key": api_key, "q": category, "page": page, "lang": "zh-CN"}
        if config.ALIBABA_1688_API_SECRET:
            params["secret"] = config.ALIBABA_1688_API_SECRET
        try:
            resp = http.get(config.ALIBABA_1688_API_URL, params=params,
                            timeout=config.REQUEST_TIMEOUT)
            resp.raise_for_status()
            payload = resp.json()
        except (requests.RequestException, ValueError) as exc:
            if page == 1:
                raise SearchAPIError(f"1688 API request failed: {exc}") from exc
            logger.warning("1688 page %d failed (%s); keeping %d results so far",
                           page, exc, len(items))
            break

        error = _api_error(payload)
        if error:
            if page == 1:
                raise SearchAPIError(f"1688 API error {error}")
            logger.warning("1688 page %d returned error %s; stopping", page, error)
            break

        page_items = _extract_items(payload)
        if not page_items:
            break
        items.extend(page_items)

        page_count = to_int((payload.get("items") or {}).get("pagecount")
                            if isinstance(payload.get("items"), dict) else None)
        if page_count and page >= page_count:
            break
    return items


def load_suppliers_file(path: str) -> List[Dict]:
    """Read raw supplier/offer records from a JSON or CSV file (manual fallback)."""
    p = Path(path).expanduser()
    if not p.is_file():
        raise FileNotFoundError(f"Supplier file not found: {p}")
    if p.suffix.lower() == ".csv":
        with p.open(encoding="utf-8-sig", newline="") as fh:
            return list(csv.DictReader(fh))
    with p.open(encoding="utf-8") as fh:
        payload = json.load(fh)
    items = _extract_items(payload)
    if not items:
        raise ValueError(f"No supplier records found in {p}")
    return items


def _print_header(category: str, location: str, moq_max: int, platform_req: str) -> None:
    print("Searching 1688 with constraints...")
    print(f"  Category: {category}")
    print(f"  Location: {location}")
    print(f"  MOQ limit: ≤{moq_max} units")
    print(f"  Platform: {config.PLATFORM_LABELS[platform_req]}")


def filter_raw_records(raw_records: List[Dict], location: str, moq_max: int,
                       platform_req: str) -> SupplierList:
    """Normalise -> group -> constrain, plus the user-facing count messages."""
    suppliers = group_by_supplier([normalise_record(r) for r in raw_records])
    result = apply_constraints(suppliers, location, moq_max, platform_req)

    if not result:
        print("No suppliers found matching constraints. Try different location or MOQ.")
        raise NoSuppliersFound(
            f"0 of {result.total_found} suppliers met the constraints "
            f"(excluded: {result.excluded})"
        )
    print(f"✓ Found {len(result)} suppliers matching all constraints "
          f"(out of {result.total_found} unique suppliers found)")
    if len(result) < config.FEW_SUPPLIERS_WARNING:
        print("⚠ Very few suppliers found. Results may be incomplete.")
    return result


def search_1688_with_constraints(
    category: str,
    location: str,
    moq_max: int,
    platform_req: str,  # "gold_supplier" | "verified_badge" | "any"
    api_key: str,
    *,
    session=None,
) -> SupplierList:
    """
    Search 1688 with hard constraints. Returns ALL matching suppliers (not limited to 10).

    Args:
        category: Product name
        location: Province/city (e.g., "Guangdong")
        moq_max: Maximum MOQ acceptable
        platform_req: Platform badge requirement
        api_key: 1688 API key

    Returns:
        SupplierList (a list of supplier dicts) with `.total_found` = unique
        suppliers seen before the constraints were applied.

    Raises:
        SearchAPIError: the API failed (caller should offer the manual fallback)
        NoSuppliersFound: nothing met the constraints
    """
    platform_req = config.normalize_platform_req(platform_req)
    _print_header(category, location, moq_max, platform_req)
    try:
        raw = fetch_1688_offers(category, api_key, session=session)
    except SearchAPIError as exc:
        print(f"✗ {exc}")
        raise
    return filter_raw_records(raw, location, moq_max, platform_req)
