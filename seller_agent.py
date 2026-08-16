import os
import json
import logging
import requests
import time
from datetime import datetime
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

ZHIPU_API_KEY = os.getenv("ZHIPU_API_KEY")
ZHIPU_API_URL = "https://open.bigmodel.cn/api/paas/v4/chat/completions"

SUPPLIER_DATABASE = [
    {"name": "JKL Export Group", "platform": "Alibaba", "country": "China", "city": "Guangzhou", 
     "years_active": 18, "review_count": 521, "rating": 4.8, "email": "sales@jklexport.com", 
     "phone": "+86-20-8765-4321", "wechat": "jkl_export_2024", "categories": ["electronics", "machinery", "textiles", "components"]},
    {"name": "NOP Distribution", "platform": "Made-in-China", "country": "China", "city": "Shenzhen",
     "years_active": 15, "review_count": 280, "rating": 4.7, "email": "info@nopdist.com",
     "phone": "+86-755-2345-6789", "wechat": "nop_distribution", "categories": ["electronics", "consumer_goods", "retail"]},
    {"name": "YZA Enterprise", "platform": "Global Sources", "country": "China", "city": "Shanghai",
     "years_active": 14, "review_count": 312, "rating": 4.6, "email": "contact@yzaent.com",
     "phone": "+86-21-5999-8888", "wechat": "yza_enterprise", "categories": ["apparel", "textiles", "fashion", "home_goods"]},
    {"name": "GHI Manufacturing", "platform": "YiwuGo", "country": "China", "city": "Yiwu",
     "years_active": 15, "review_count": 342, "rating": 4.5, "email": "sales@ghimfg.com",
     "phone": "+86-579-8765-4321", "wechat": "ghi_manufacturing", "categories": ["gifts", "toys", "small_goods", "crafts"]},
    {"name": "BCD International", "platform": "Made-in-China", "country": "China", "city": "Beijing",
     "years_active": 11, "review_count": 267, "rating": 4.4, "email": "hello@bcdintl.com",
     "phone": "+86-10-6789-5432", "wechat": "bcd_international", "categories": ["machinery", "industrial", "equipment"]},
    {"name": "ABC Trading Co.", "platform": "Alibaba", "country": "China", "city": "Hangzhou",
     "years_active": 15, "review_count": 342, "rating": 4.8, "email": "info@abctrading.com",
     "phone": "+86-571-8765-4321", "wechat": "abc_trading_hq", "categories": ["electronics", "led", "lighting", "industrial"]},
    {"name": "XYZ Imports Ltd.", "platform": "Global Sources", "country": "China", "city": "Xiamen",
     "years_active": 12, "review_count": 218, "rating": 4.6, "email": "sales@xyzimports.com",
     "phone": "+86-592-1234-5678", "wechat": "xyz_imports", "categories": ["furniture", "home_goods", "decor"]},
    {"name": "DEF Supply Chain", "platform": "Made-in-China", "country": "China", "city": "Chongqing",
     "years_active": 8, "review_count": 156, "rating": 4.3, "email": "contact@defsupply.com",
     "phone": "+86-23-6789-1234", "wechat": "def_supply_chain", "categories": ["logistics", "packaging", "shipping"]},
    {"name": "MNO Industrial", "platform": "Global Sources", "country": "Vietnam", "city": "Ho Chi Minh",
     "years_active": 7, "review_count": 124, "rating": 4.2, "email": "info@mnoindustrial.com",
     "phone": "+84-28-1234-5678", "wechat": "mno_industrial", "categories": ["textiles", "apparel", "garments"]},
    {"name": "PQR Solutions", "platform": "Made-in-China", "country": "China", "city": "Suzhou",
     "years_active": 11, "review_count": 267, "rating": 4.5, "email": "sales@pqrsolutions.com",
     "phone": "+86-512-8765-4321", "wechat": "pqr_solutions", "categories": ["electronics", "semiconductors", "components"]},
    {"name": "STU Trading", "platform": "YiwuGo", "country": "China", "city": "Yiwu",
     "years_active": 9, "review_count": 195, "rating": 4.4, "email": "hello@stutrading.com",
     "phone": "+86-579-1234-5678", "wechat": "stu_trading", "categories": ["gifts", "novelties", "small_goods"]},
    {"name": "VWX Commerce", "platform": "Alibaba", "country": "India", "city": "Mumbai",
     "years_active": 6, "review_count": 98, "rating": 4.1, "email": "contact@vwxcommerce.com",
     "phone": "+91-22-1234-5678", "wechat": "vwx_commerce_india", "categories": ["textiles", "spices", "handicrafts"]},
    {"name": "KLM Wholesale", "platform": "Global Sources", "country": "Thailand", "city": "Bangkok",
     "years_active": 9, "review_count": 201, "rating": 4.3, "email": "sales@klmwholesale.com",
     "phone": "+66-2-1234-5678", "wechat": "klm_wholesale", "categories": ["electronics", "appliances", "consumer_goods"]},
    {"name": "EFG Logistics", "platform": "YiwuGo", "country": "China", "city": "Yiwu",
     "years_active": 5, "review_count": 87, "rating": 4.0, "email": "info@efglogistics.com",
     "phone": "+86-579-9999-8888", "wechat": "efg_logistics", "categories": ["logistics", "fulfillment", "warehousing"]},
    {"name": "HIJ Factory", "platform": "Alibaba", "country": "China", "city": "Dongguan",
     "years_active": 11, "review_count": 267, "rating": 4.5, "email": "sales@hijfactory.com",
     "phone": "+86-769-1234-5678", "wechat": "hij_factory", "categories": ["electronics", "iot", "smart_devices"]},
]


def make_api_call_with_retry(payload, max_retries=3):
    if not ZHIPU_API_KEY:
        return None
    
    for attempt in range(max_retries):
        try:
            headers = {
                "Authorization": f"Bearer {ZHIPU_API_KEY}",
                "Content-Type": "application/json"
            }
            
            response = requests.post(ZHIPU_API_URL, headers=headers, json=payload, timeout=30)
            
            if response.status_code == 200:
                return response
            
            if attempt < max_retries - 1:
                time.sleep(2)
        except:
            if attempt < max_retries - 1:
                time.sleep(2)
    
    return None


def filter_relevant_suppliers(product_name, suppliers):
    product_keywords = product_name.lower().split()
    
    for supplier in suppliers:
        score = 0
        supplier_categories = " ".join(supplier.get("categories", [])).lower()
        
        for keyword in product_keywords:
            if keyword in supplier_categories:
                score += 25
            if keyword in supplier["name"].lower():
                score += 15
        
        supplier["relevance_score"] = max(0, min(100, score + supplier["rating"] * 5))
    
    suppliers.sort(key=lambda x: x["relevance_score"], reverse=True)
    return suppliers[:10]


def analyze_and_rank_suppliers(product_name, suppliers, market_data):
    suppliers_text = ""
    for i, supplier in enumerate(suppliers[:5], 1):
        suppliers_text += f"\nSupplier {i}: {supplier['name']} | {supplier['platform']} | Rating: {supplier['rating']}/5 | Relevance: {supplier.get('relevance_score', 0):.0f}%"
    
    prompt = f"""Rank these suppliers for {product_name} from 1-10 based on experience, rating, and product fit.
Return ONLY JSON with no markdown:
{{"rankings": [{{"rank": 1, "name": "Company Name", "score": 9.2, "key_strength": "strength description"}}]}}

Suppliers:{suppliers_text}"""
    
    payload = {
        "model": "glm-4-flash",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3,
    }
    
    response = make_api_call_with_retry(payload)
    
    if not response:
        return suppliers[:5]
    
    try:
        result = response.json()
        analysis_text = result['choices'][0]['message']['content']
        
        json_start = analysis_text.find('{')
        json_end = analysis_text.rfind('}') + 1
        json_str = analysis_text[json_start:json_end]
        analysis = json.loads(json_str)
        
        for ranking in analysis.get("rankings", []):
            for supplier in suppliers:
                if supplier['name'].lower() in ranking['name'].lower():
                    supplier['ai_score'] = ranking['score']
                    supplier['key_strength'] = ranking['key_strength']
        
        return suppliers[:5]
    except:
        return suppliers[:5]


def fetch_market_data(product_name):
    return {
        "product": product_name,
        "price_range_low": 15,
        "price_range_high": 450,
        "price_unit": "USD",
        "min_order": 100,
        "min_order_unit": "units",
        "certifications": ["CE", "FCC", "ISO 9001"],
        "lead_time_low": 20,
        "lead_time_high": 45,
        "lead_time_unit": "days",
        "typical_source": "China",
        "shipping_methods": ["Sea Freight", "Air Express"],
        "payment_terms": "T/T 50/50, L/C 90 days",
    }


def run_agent(product_name):
    try:
        all_suppliers = [s.copy() for s in SUPPLIER_DATABASE]
        relevant_suppliers = filter_relevant_suppliers(product_name, all_suppliers)
        market = fetch_market_data(product_name)
        top_suppliers = analyze_and_rank_suppliers(product_name, relevant_suppliers, market)
        
        return {
            "product": product_name,
            "total_database": len(SUPPLIER_DATABASE),
            "relevant_suppliers": len(relevant_suppliers),
            "top_5": top_suppliers[:5],
            "market_data": market,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {"error": str(e)}


if __name__ == "__main__":
    result = run_agent("LED lights")
    print(json.dumps(result, indent=2))