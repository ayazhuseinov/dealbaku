"""Shared helpers: number parsing, percentile maths, location matching."""

import re
import statistics
from datetime import date
from typing import Iterable, List, Optional

_NUM_RE = re.compile(r"\d+(?:\.\d+)?")


def to_float(value) -> Optional[float]:
    """Parse '¥18.50', '4.7', '1,200' or 18 into a float; None if absent."""
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    match = _NUM_RE.search(str(value).replace(",", ""))
    return float(match.group()) if match else None


def to_int(value) -> Optional[int]:
    num = to_float(value)
    return int(num) if num is not None else None


def parse_range(value):
    """'18-22', '¥18~¥22', [18, 22] or 18 -> (18.0, 22.0). Missing -> (None, None)."""
    if value is None:
        return None, None
    if isinstance(value, (list, tuple)):
        nums = [to_float(v) for v in value]
    else:
        nums = [float(n) for n in _NUM_RE.findall(str(value).replace(",", ""))]
    nums = [n for n in nums if n is not None]
    if not nums:
        return None, None
    return min(nums), max(nums)


def years_in_business(raw, today: Optional[date] = None) -> Optional[int]:
    """
    Accepts a join year ('joined 2019', 2019, '2019-03-01'), a 1688 tenure
    string ('入驻7年', '7 years') or a plain small integer (already years).
    """
    if raw is None:
        return None
    current_year = (today or date.today()).year
    text = str(raw)
    year_match = re.search(r"(19|20)\d{2}", text)
    if year_match:
        return max(0, current_year - int(year_match.group()))
    num = to_int(text)
    return num if num is not None and num < 100 else None


def percentile_score(value: Optional[float], lo: Optional[float], hi: Optional[float]) -> float:
    """
    Min-max position within the observed range, 0-100:
    (value - min) / (max - min) * 100. Missing values score 0; when every
    supplier has the same value, all score 100 (nobody is behind).
    """
    if value is None or lo is None or hi is None:
        return 0.0
    if hi == lo:
        return 100.0
    return max(0.0, min(100.0, (value - lo) / (hi - lo) * 100))


def describe(values: Iterable[Optional[float]]) -> dict:
    """min/max/median/mean/75th percentile over the non-missing values."""
    clean: List[float] = sorted(v for v in values if v is not None)
    if not clean:
        return {"count": 0, "min": None, "max": None, "median": None, "mean": None,
                "top_quartile_threshold": None}
    if len(clean) == 1:
        q3 = clean[0]
    else:
        q3 = statistics.quantiles(clean, n=4, method="inclusive")[2]
    return {
        "count": len(clean),
        "min": clean[0],
        "max": clean[-1],
        "median": statistics.median(clean),
        "mean": statistics.fmean(clean),
        "top_quartile_threshold": q3,
    }


def tidy(num: Optional[float], ndigits: int = 2):
    """Round, and drop the .0 from whole numbers so JSON reads 15 not 15.0."""
    if num is None:
        return None
    num = round(float(num), ndigits)
    return int(num) if num.is_integer() else num


# English -> Chinese for provinces and the big sourcing cities, so a user
# typing "Guangdong" still matches a 1688 listing that says "广东 广州".
LOCATION_ALIASES = {
    "guangdong": "广东", "zhejiang": "浙江", "jiangsu": "江苏", "fujian": "福建",
    "shandong": "山东", "hebei": "河北", "henan": "河南", "hubei": "湖北",
    "hunan": "湖南", "anhui": "安徽", "jiangxi": "江西", "sichuan": "四川",
    "liaoning": "辽宁", "jilin": "吉林", "heilongjiang": "黑龙江", "shanxi": "山西",
    "shaanxi": "陕西", "yunnan": "云南", "guizhou": "贵州", "guangxi": "广西",
    "hainan": "海南", "gansu": "甘肃", "qinghai": "青海", "inner mongolia": "内蒙古",
    "xinjiang": "新疆", "tibet": "西藏", "ningxia": "宁夏",
    "shanghai": "上海", "beijing": "北京", "tianjin": "天津", "chongqing": "重庆",
    "guangzhou": "广州", "shenzhen": "深圳", "dongguan": "东莞", "foshan": "佛山",
    "shantou": "汕头", "zhongshan": "中山", "huizhou": "惠州", "jiangmen": "江门",
    "hangzhou": "杭州", "ningbo": "宁波", "yiwu": "义乌", "jinhua": "金华",
    "wenzhou": "温州", "taizhou": "台州", "shaoxing": "绍兴", "huzhou": "湖州",
    "suzhou": "苏州", "wuxi": "无锡", "nantong": "南通", "changzhou": "常州",
    "nanjing": "南京", "xiamen": "厦门", "quanzhou": "泉州", "fuzhou": "福州",
    "putian": "莆田", "jinjiang": "晋江", "qingdao": "青岛", "linyi": "临沂",
    "yantai": "烟台", "jinan": "济南", "baoding": "保定", "shijiazhuang": "石家庄",
    "wuhan": "武汉", "chengdu": "成都", "zhengzhou": "郑州", "hefei": "合肥",
}


def location_matches(supplier_location: Optional[str], wanted: Optional[str]) -> bool:
    if not wanted:
        return True
    if not supplier_location:
        return False
    haystack = supplier_location.lower()
    needle = wanted.strip().lower()
    candidates = {needle, needle.removesuffix(" province"), needle.removesuffix(" city")}
    for name in list(candidates):
        if name in LOCATION_ALIASES:
            candidates.add(LOCATION_ALIASES[name])
    # Reverse lookup so a Chinese input also matches English listings.
    for en, cn in LOCATION_ALIASES.items():
        if cn in candidates or cn.rstrip("省市") in candidates:
            candidates.add(en)
    return any(c and c in haystack for c in candidates)


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_") or "product"
