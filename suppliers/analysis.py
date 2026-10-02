"""
STEP 5 - Ask GLM-5.3 (via NVIDIA's OpenAI-compatible endpoint) to assess the top 5.

A failed call never sinks the report: the supplier gets a glm_analysis with
an "error" key and the run continues.
"""

import json
import logging
import re
from typing import Dict, List, Optional

from utils import config

logger = logging.getLogger(__name__)

VALID_RECOMMENDATIONS = ("recommend_first", "recommend_second", "consider_backup")


def build_prompt(supplier: Dict, product_category: str) -> str:
    return f"""Analyze this supplier for sourcing {product_category}:

Name: {supplier['company_name_en']}
Location: {supplier['location']}
Years in business: {supplier['years_in_business']}
Feedback rating: {supplier['customer_feedback_rating']}/5 ({supplier['review_count']} reviews)
MOQ: {supplier['moq_min']}-{supplier['moq_max']} units
Price range: ¥{supplier['price_min']}-{supplier['price_max']} per unit
Platform badge: {supplier['platform_badge']}
Contact: WeChat={supplier['wechat_contact']}, Phone={supplier['phone_number']}

Provide ONLY a JSON response:
{{
  "quality_confidence": 1-10,
  "supply_reliability": 1-10,
  "key_strength": "one sentence",
  "main_risk": "one sentence",
  "negotiation_leverage": "one sentence (e.g., 'Multiple reviews show reliability; can negotiate bulk discount')",
  "recommendation": "recommend_first | recommend_second | consider_backup"
}}
"""


def parse_json_reply(text: str) -> Dict:
    """Tolerate <think> blocks and ```json fences around the object."""
    text = re.sub(r"<think>.*?</think>", "", text or "", flags=re.S).strip()
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end <= start:
        raise ValueError(f"No JSON object in model reply: {text[:200]!r}")
    data = json.loads(text[start:end + 1])
    for key in ("quality_confidence", "supply_reliability"):
        if key in data:
            try:
                data[key] = max(1, min(10, int(round(float(data[key])))))
            except (TypeError, ValueError):
                pass
    if data.get("recommendation") not in VALID_RECOMMENDATIONS:
        data["recommendation"] = "consider_backup"
    return data


def _complete(client, prompt: str) -> str:
    kwargs = dict(
        model=config.GLM_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.5,
        max_tokens=512,
    )
    try:
        response = client.chat.completions.create(
            response_format={"type": "json_object"}, **kwargs)
    except Exception as exc:  # some NIM deployments reject response_format
        logger.info("Retrying without response_format (%s)", exc)
        response = client.chat.completions.create(**kwargs)
    return response.choices[0].message.content or ""


def make_client(api_key: str):
    from openai import OpenAI

    return OpenAI(base_url=config.NVIDIA_BASE_URL, api_key=api_key)


def analyze_with_glm5(top_5: List[Dict], product_category: str,
                      api_key: Optional[str] = None, *, client=None) -> List[Dict]:
    """Attach `glm_analysis` to each supplier and return the list."""
    if client is None:
        if not api_key:
            raise ValueError("No NVIDIA API key provided (--nvidia-key or NVIDIA_API_KEY).")
        client = make_client(api_key)

    print(f"Analyzing top {len(top_5)} with GLM-5.3...")
    for supplier in top_5:
        name = supplier.get("company_name_en") or supplier.get("supplier_id")
        try:
            reply = _complete(client, build_prompt(supplier, product_category))
            supplier["glm_analysis"] = parse_json_reply(reply)
            print(f"  ✓ {name} analyzed")
        except Exception as exc:
            logger.warning("GLM analysis failed for %s: %s", name, exc)
            supplier["glm_analysis"] = {"error": str(exc)}
            print(f"  ✗ {name}: GLM analysis failed ({exc})")
    return top_5
