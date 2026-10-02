import json
from datetime import date
from pathlib import Path
from types import SimpleNamespace

import pytest

import main
from reports.generator import generate_report
from suppliers import analysis, extraction, search_1688
from suppliers.distribution import analyze_distribution
from suppliers.ranking import rank_suppliers_by_percentile
from suppliers.search_1688 import (NoSuppliersFound, SearchAPIError, apply_constraints,
                                   fetch_1688_offers, filter_raw_records, group_by_supplier,
                                   normalise_record)
from utils import config
from utils.helpers import (describe, location_matches, parse_range, percentile_score,
                           years_in_business)

SAMPLE = Path(__file__).resolve().parent.parent / "data" / "sample_suppliers_dog_beds.json"


def supplier(**overrides):
    base = {
        "seller_id": "s1", "company_name_en": "Test Co", "company_name_cn": "测试公司",
        "store_link": "https://test.1688.com", "platform_badge": "gold", "joined": "2016",
        "city": "Guangzhou", "province": "Guangdong", "rating": 4.5, "review_count": 100,
        "moq_min": 50, "moq_max": 500, "price_min": 18, "price_max": 22,
        "wechat": "wx_test", "phone": "13800138000", "email": "a@test.example.com",
    }
    base.update(overrides)
    return base


# --- helpers ---------------------------------------------------------------

def test_years_in_business_formats():
    today = date(2026, 9, 23)
    assert years_in_business("joined 2019", today) == 7
    assert years_in_business(2019, today) == 7
    assert years_in_business("入驻12年", today) == 12
    assert years_in_business(None, today) is None


def test_percentile_score_matches_spec_example():
    assert round(percentile_score(10, 1, 15)) == 64
    assert round(percentile_score(4.7, 3.2, 5.0)) == 83
    assert round(percentile_score(200, 5, 500)) == 39
    assert percentile_score(None, 1, 15) == 0
    assert percentile_score(5, 5, 5) == 100


def test_describe_quartile():
    stats = describe([1, 2, 3, 4, 5, 6, 7, 8, None])
    assert stats["median"] == 4.5 and stats["top_quartile_threshold"] == 6.25
    assert describe([])["min"] is None
    assert describe([3])["top_quartile_threshold"] == 3


def test_parse_range_and_location():
    assert parse_range("¥18.5-¥22") == (18.5, 22.0)
    assert parse_range(None) == (None, None)
    assert location_matches("广东 广州", "Guangdong")
    assert location_matches("Shenzhen, Guangdong", "guangdong province")
    assert location_matches("Shenzhen, Guangdong", "广东")
    assert not location_matches("Yiwu, Zhejiang", "Guangdong")
    assert not location_matches(None, "Guangdong")


# --- step 1 ----------------------------------------------------------------

def test_normalise_handles_chinese_and_gateway_fields():
    rec = normalise_record({"nick": "shopA", "会员类型": "诚信通", "tp_year": "6",
                            "location": "广东 东莞", "score": 96, "price": "12.5-15",
                            "quantity_begin": "2", "detail_url": "https://detail.1688.com/x"})
    assert rec["platform_badge"] == "gold"
    assert rec["years_in_business"] == 6
    assert rec["customer_feedback_rating"] == 4.8
    assert (rec["price_min"], rec["price_max"]) == (12.5, 15)
    assert rec["moq_min"] == 2
    assert rec["business_registration_status"] == "verified"
    assert rec["avg_shipping_days"] == "unknown"


def test_grouping_merges_offers_from_same_seller():
    a = normalise_record(supplier(price_min=18, price_max=20, moq_min=100, wechat=None))
    b = normalise_record(supplier(price_min=15, price_max=25, moq_min=50, wechat="wx2"))
    [merged] = group_by_supplier([a, b])
    assert (merged["price_min"], merged["price_max"]) == (15, 25)
    assert merged["moq_min"] == 50
    assert merged["wechat_contact"] == "wx2"
    assert merged["offer_count"] == 2


def test_constraints_filter_and_number_suppliers():
    recs = [normalise_record(r) for r in (
        supplier(seller_id="ok"),
        supplier(seller_id="far", city="Yiwu", province="Zhejiang"),
        supplier(seller_id="bigmoq", moq_min=1000),
        supplier(seller_id="nomoq", moq_min=None, moq_max=None),
        supplier(seller_id="verified", platform_badge="verified"),
        supplier(seller_id="regular", platform_badge="regular"),
    )]
    gold = apply_constraints(recs, "Guangdong", 500, "gold_supplier_only")
    assert [s["supplier_id"] for s in gold] == ["SUP-0001"]
    assert gold.total_found == 6
    assert gold.excluded == {"location": 1, "moq": 2, "platform": 2}
    assert len(apply_constraints(recs, "Guangdong", 500, "verified_badge")) == 2
    assert len(apply_constraints(recs, "Guangdong", 500, "any")) == 3


def test_no_suppliers_raises(capsys):
    with pytest.raises(NoSuppliersFound):
        filter_raw_records([supplier(city="Yiwu", province="Zhejiang")], "Guangdong", 500, "any")
    assert "No suppliers found matching constraints" in capsys.readouterr().out


def test_few_suppliers_warns(capsys):
    filter_raw_records([supplier()], "Guangdong", 500, "any")
    assert "Very few suppliers found" in capsys.readouterr().out


class FakeResponse:
    def __init__(self, payload, status=200, text=""):
        self._payload, self.status_code, self.text = payload, status, text

    def raise_for_status(self):
        if self.status_code >= 400:
            import requests
            raise requests.HTTPError(f"{self.status_code}")

    def json(self):
        return self._payload


class FakeSession:
    def __init__(self, responses):
        self.responses, self.calls = list(responses), []

    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return self.responses.pop(0) if self.responses else FakeResponse({"items": {"item": []}})


def test_fetch_walks_all_pages():
    session = FakeSession([
        FakeResponse({"items": {"item": [supplier(seller_id="a")], "pagecount": 3}}),
        FakeResponse({"items": {"item": [supplier(seller_id="b")], "pagecount": 3}}),
        FakeResponse({"items": {"item": [supplier(seller_id="c")], "pagecount": 3}}),
    ])
    items = fetch_1688_offers("dog beds", "k", session=session)
    assert [i["seller_id"] for i in items] == ["a", "b", "c"]
    assert [c[1]["params"]["page"] for c in session.calls] == [1, 2, 3]


def test_fetch_raises_on_api_error():
    session = FakeSession([FakeResponse({"error_code": "4013", "error": "bad key"})])
    with pytest.raises(SearchAPIError, match="bad key"):
        fetch_1688_offers("dog beds", "k", session=session)
    with pytest.raises(SearchAPIError):
        fetch_1688_offers("dog beds", "k", session=FakeSession([FakeResponse({}, status=500)]))
    with pytest.raises(SearchAPIError):
        fetch_1688_offers("dog beds", "", session=FakeSession([]))


# --- steps 2 & 3 -----------------------------------------------------------

def _suppliers():
    return filter_raw_records(search_1688.load_suppliers_file(str(SAMPLE)),
                              "Guangdong", 500, "gold_supplier")


def test_distribution_and_ranking_on_sample():
    suppliers = _suppliers()
    dist = analyze_distribution(suppliers)
    assert dist["supplier_count"] == len(suppliers)
    years = dist["years_in_business"]
    assert years["min"] <= years["median"] <= years["top_quartile_threshold"] <= years["max"]
    assert dist["market_pricing"]["min_price"] <= dist["market_pricing"]["average_price"]

    top = rank_suppliers_by_percentile(suppliers, dist)
    assert len(top) == 10
    scores = [s["score"] for s in top]
    assert scores == sorted(scores, reverse=True)
    assert all(0 <= s["score"] <= 95 for s in suppliers)


def test_ranking_weights():
    suppliers = [normalise_record(supplier(seller_id=str(i), joined=str(2026 - y), rating=r,
                                           review_count=c, platform_badge=b))
                 for i, (y, r, c, b) in enumerate([(1, 3.2, 5, "regular"),
                                                   (15, 5.0, 500, "gold"),
                                                   (10, 4.7, 200, "verified")])]
    for s in suppliers:
        s["years_in_business"] = int(s["years_in_business"])
    dist = analyze_distribution(suppliers)
    ranked = rank_suppliers_by_percentile(suppliers, dist, limit=None)
    assert ranked[0]["score"] == 95.0          # 25 + 35 + 25 + 10
    assert ranked[-1]["score"] == 0.0
    mid = ranked[1]
    expected = 9 / 14 * 100 * 0.25 + 1.5 / 1.8 * 100 * 0.35 + 195 / 495 * 100 * 0.25 + 5
    assert mid["score"] == round(expected, 1)


# --- step 4 ----------------------------------------------------------------

def test_parse_contacts():
    html = "<div>微信：petmaster_gz88</div><span>手机 13912345678</span> sales@pm.example.com"
    assert extraction.parse_contacts(html) == {
        "email": "sales@pm.example.com", "phone_number": "13912345678",
        "wechat_contact": "petmaster_gz88"}


def test_extraction_scrapes_then_marks_missing(capsys):
    s = normalise_record(supplier(wechat=None, email=None, store_link="https://abc.1688.com"))
    session = FakeSession([FakeResponse({}, text="no contacts here"),
                           FakeResponse({}, text="WeChat: abc_wechat")])
    [out] = extraction.extract_complete_contact_data([s], session=session)
    assert out["wechat_contact"] == "abc_wechat"
    assert out["email"] == config.NOT_LISTED
    assert session.calls[1][0] == "https://abc.1688.com/page/contactinfo.htm"


# --- step 5 ----------------------------------------------------------------

GOOD_REPLY = json.dumps({
    "quality_confidence": 9, "supply_reliability": 8, "key_strength": "Solid factory",
    "main_risk": "Pricey", "negotiation_leverage": "Volume", "recommendation": "recommend_first"})


class FakeClient:
    def __init__(self, replies):
        self.replies, self.kwargs = list(replies), []
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    def _create(self, **kwargs):
        self.kwargs.append(kwargs)
        reply = self.replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        msg = SimpleNamespace(content=reply)
        return SimpleNamespace(choices=[SimpleNamespace(message=msg)])


def test_glm_analysis_success_and_failure(capsys):
    s1, s2 = (normalise_record(supplier(seller_id=x)) for x in "ab")
    client = FakeClient([f"<think>hmm</think>```json\n{GOOD_REPLY}\n```", "not json"])
    analysis.analyze_with_glm5([s1, s2], "dog beds", client=client)
    assert s1["glm_analysis"]["recommendation"] == "recommend_first"
    assert "error" in s2["glm_analysis"]
    assert client.kwargs[0]["model"] == config.GLM_MODEL
    assert client.kwargs[0]["response_format"] == {"type": "json_object"}
    assert "dog beds" in client.kwargs[0]["messages"][0]["content"]


def test_glm_retries_without_response_format():
    s = normalise_record(supplier())
    client = FakeClient([RuntimeError("response_format unsupported"), GOOD_REPLY])
    analysis.analyze_with_glm5([s], "dog beds", client=client)
    assert s["glm_analysis"]["quality_confidence"] == 9
    assert "response_format" not in client.kwargs[1]


# --- step 6 / end to end ----------------------------------------------------

def test_generate_report_files(tmp_path, capsys):
    suppliers = _suppliers()
    dist = analyze_distribution(suppliers)
    top_10 = rank_suppliers_by_percentile(suppliers, dist)
    out = generate_report(top_10[:5], dist, suppliers.total_found,
                          context={"product": "dog beds", "location": "Guangdong", "moq": 500,
                                   "platform": "gold_supplier", "search_date": "2026-09-23"},
                          top_10=top_10, output_dir=str(tmp_path))
    assert out["json_path"].name == "dealbaku_supplier_analysis_dog_beds_2026-09-23.json"
    data = json.loads(out["json_path"].read_text(encoding="utf-8"))
    assert data["total_suppliers_found"] == suppliers.total_found
    assert data["suppliers_meeting_constraints"] == len(suppliers)
    assert [s["rank"] for s in data["top_5_suppliers"]] == [1, 2, 3, 4, 5]
    assert set(data["distribution"]) == {"years_in_business", "feedback_rating",
                                         "review_count", "market_pricing"}
    assert "SUPPLIER DISCOVERY REPORT — Dog Beds" in capsys.readouterr().out


def test_main_end_to_end_with_file(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(analysis, "make_client", lambda key: FakeClient([GOOD_REPLY] * 5))
    code = main.run(["--product", "dog beds", "--location", "Guangdong", "--moq", "500",
                     "--platform", "gold_supplier", "--suppliers-file", str(SAMPLE),
                     "--nvidia-key", "nvapi_test", "--no-scrape", "--output-dir", str(tmp_path)])
    assert code == 0
    [report] = tmp_path.glob("*.json")
    data = json.loads(report.read_text(encoding="utf-8"))
    assert all(s["glm_analysis"]["recommendation"] == "recommend_first"
               for s in data["top_5_suppliers"])
    assert len(data["all_suppliers"]) == data["suppliers_meeting_constraints"]
    assert "RECOMMEND FIRST" in capsys.readouterr().out


def test_main_requires_nvidia_key(monkeypatch, capsys):
    monkeypatch.delenv("NVIDIA_API_KEY", raising=False)
    code = main.run(["--product", "x", "--location", "Guangdong", "--moq", "5",
                     "--suppliers-file", str(SAMPLE)])
    assert code == 2


def test_main_api_failure_non_interactive(monkeypatch, capsys):
    def boom(*a, **k):
        raise SearchAPIError("down")
    monkeypatch.setattr(main, "search_1688_with_constraints", boom)
    code = main.run(["--product", "x", "--location", "Guangdong", "--moq", "5",
                     "--1688-key", "k", "--skip-glm"])
    assert code == 1
    assert "--suppliers-file" in capsys.readouterr().out
