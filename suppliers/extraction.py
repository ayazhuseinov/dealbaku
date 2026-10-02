"""
STEP 4 - Make sure the top suppliers have complete contact data.

For any missing WeChat / phone / email, the supplier's 1688 store page and its
contact page (/page/contactinfo.htm) are fetched and scanned. 1688 often hides
contacts behind login or anti-bot checks, so this is best-effort: whatever is
still missing afterwards is marked "not publicly listed".
"""

import logging
import re
from typing import Dict, List, Optional

import requests

from utils import config

logger = logging.getLogger(__name__)

CONTACT_FIELDS = ("wechat_contact", "phone_number", "email")
REQUIRED_FIELDS = ("store_link", "location", "company_name_cn", "company_name_en") + CONTACT_FIELDS

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
MOBILE_RE = re.compile(r"(?<!\d)(?:\+?86[-\s]?)?1[3-9]\d{9}(?!\d)")
LANDLINE_RE = re.compile(r"(?<!\d)(?:\+?86[-\s]?)?0\d{2,3}[-\s]?\d{7,8}(?!\d)")
WECHAT_RE = re.compile(r"(?:微信|wechat|weixin|WeChat|VX|vx)\s*(?:号)?\s*[:：]?\s*([A-Za-z][-_A-Za-z0-9]{5,19})")

HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"),
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}


def parse_contacts(html: str) -> Dict[str, Optional[str]]:
    """Pull the first email, phone and WeChat ID out of a store page."""
    text = re.sub(r"<[^>]+>", " ", html or "")
    emails = [e for e in EMAIL_RE.findall(text)
              if not e.lower().endswith((".png", ".jpg", ".gif", ".webp"))]
    phone = MOBILE_RE.search(text) or LANDLINE_RE.search(text)
    wechat = WECHAT_RE.search(text)
    return {
        "email": emails[0] if emails else None,
        "phone_number": phone.group().strip() if phone else None,
        "wechat_contact": wechat.group(1) if wechat else None,
    }


def _contact_pages(store_link: str) -> List[str]:
    base = store_link.rstrip("/")
    pages = [store_link]
    if ".1688.com" in base and "/page/contactinfo" not in base:
        pages.append(base.split("/page/")[0] + "/page/contactinfo.htm")
    return pages


def scrape_store_contacts(store_link: str, session=None) -> Dict[str, Optional[str]]:
    http = session or requests
    found: Dict[str, Optional[str]] = {f: None for f in CONTACT_FIELDS}
    for url in _contact_pages(store_link):
        try:
            resp = http.get(url, headers=HEADERS, timeout=config.REQUEST_TIMEOUT)
            if resp.status_code != 200:
                continue
            for field, value in parse_contacts(resp.text).items():
                found[field] = found[field] or value
        except requests.RequestException as exc:
            logger.debug("Could not fetch %s: %s", url, exc)
        if all(found.values()):
            break
    return found


def _missing(value) -> bool:
    return value in (None, "", config.NOT_LISTED)


def extract_complete_contact_data(top_10: List[Dict], *, scrape: bool = True,
                                  session=None) -> List[Dict]:
    """Fill gaps from the store page, then mark anything still empty."""
    for s in top_10:
        gaps = [f for f in CONTACT_FIELDS if _missing(s.get(f))]
        if gaps and scrape and s.get("store_link"):
            scraped = scrape_store_contacts(s["store_link"], session=session)
            for field in gaps:
                if scraped.get(field):
                    s[field] = scraped[field]
        for field in REQUIRED_FIELDS:
            if _missing(s.get(field)):
                s[field] = config.NOT_LISTED
    complete = sum(1 for s in top_10
                   if all(s[f] != config.NOT_LISTED for f in CONTACT_FIELDS))
    print(f"WeChat, phone, email extracted for {complete} of top {len(top_10)}"
          + ("" if complete == len(top_10) else " (rest marked 'not publicly listed')"))
    return top_10
