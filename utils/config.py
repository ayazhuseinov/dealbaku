"""Configuration: API keys, endpoints, constraint names and scoring weights."""

import os
from dataclasses import dataclass
from typing import Optional

from dotenv import load_dotenv

load_dotenv()

# --- Endpoints -------------------------------------------------------------
# 1688 has no public keyword-search API that works with a bare key; most teams
# go through a data gateway. The client sends GET {URL}?key=...&q=...&page=N
# and normalises the common response shapes (see suppliers/search_1688.py).
ALIBABA_1688_API_URL = os.getenv(
    "ALIBABA_1688_API_URL", "https://api-gw.onebound.cn/1688/item_search/"
)
ALIBABA_1688_API_SECRET = os.getenv("ALIBABA_1688_API_SECRET", "")

NVIDIA_BASE_URL = os.getenv("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1")
GLM_MODEL = os.getenv("GLM_MODEL", "z-ai/glm-5-3")

# --- Search behaviour ------------------------------------------------------
MAX_SEARCH_PAGES = int(os.getenv("DEALBAKU_MAX_PAGES", "20"))
REQUEST_TIMEOUT = int(os.getenv("DEALBAKU_REQUEST_TIMEOUT", "30"))
FEW_SUPPLIERS_WARNING = 5

# --- Platform requirement --------------------------------------------------
PLATFORM_ANY = "any"
PLATFORM_GOLD = "gold_supplier"
PLATFORM_VERIFIED = "verified_badge"

_PLATFORM_ALIASES = {
    "any": PLATFORM_ANY,
    "gold": PLATFORM_GOLD,
    "gold_supplier": PLATFORM_GOLD,
    "gold_supplier_only": PLATFORM_GOLD,
    "verified": PLATFORM_VERIFIED,
    "verified_badge": PLATFORM_VERIFIED,
    "verified_badge_only": PLATFORM_VERIFIED,
}

PLATFORM_LABELS = {
    PLATFORM_ANY: "Any",
    PLATFORM_GOLD: "Gold Suppliers Only",
    PLATFORM_VERIFIED: "Verified Suppliers Only",
}

# --- Ranking ---------------------------------------------------------------
WEIGHT_YEARS = 0.25
WEIGHT_RATING = 0.35
WEIGHT_REVIEWS = 0.25
BADGE_BONUS = {"gold": 10, "verified": 5, "regular": 0}

TOP_RANKED = 10
TOP_ANALYZED = 5

NOT_LISTED = "not publicly listed"


def normalize_platform_req(value: str) -> str:
    key = (value or PLATFORM_ANY).strip().lower().replace("-", "_").replace(" ", "_")
    if key not in _PLATFORM_ALIASES:
        raise ValueError(
            f"Unknown platform requirement '{value}'. "
            "Use one of: gold_supplier, verified_badge, any."
        )
    return _PLATFORM_ALIASES[key]


@dataclass
class ApiKeys:
    alibaba_1688: Optional[str]
    nvidia: Optional[str]


def resolve_api_keys(cli_1688: Optional[str] = None, cli_nvidia: Optional[str] = None) -> ApiKeys:
    """CLI flags win; otherwise fall back to .env / environment."""
    return ApiKeys(
        alibaba_1688=cli_1688 or os.getenv("ALIBABA_1688_API_KEY"),
        nvidia=cli_nvidia or os.getenv("NVIDIA_API_KEY"),
    )
