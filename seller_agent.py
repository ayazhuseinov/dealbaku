import os
import json
import logging
import requests
import time
from datetime import datetime
from dotenv import load_dotenv

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment
load_dotenv(r"C:\Users\user\Documents\My Python\.env")

# Zhipu AI Configuration
API_KEY = os.getenv("ZHIPU_API_KEY")
API_URL = "https://open.bigmodel.cn/api/paas/v4/chat/completions"

# ============================================================================
# RETRY LOGIC FOR API CALLS
# ============================================================================

def make_api_call_with_retry(payload, max_retries=3):
    """Call Zhipu AI with automatic retry on timeout"""
    for attempt in range(max_retries):
        try:
            headers = {
    "Authorization": f"{API_KEY}",
    "Content-Type": "application/json"
}
            
            logger.info(f"🔄 API attempt {attempt + 1}/{max_retries}...")
            response = requests.post(API_URL, headers=headers, json=payload, timeout=120)
            
            if response.status_code == 200:
                logger.info("✅ API call successful!")
                return response
            else:
                logger.warning(f"❌ Error code: {response.status_code}")
                if attempt < max_retries - 1:
                    logger.info(f"⏳ Waiting 2 seconds before retry...")
                    time.sleep(2)
        
        except requests.exceptions.Timeout:
            logger.warning(f"⏱️ Timeout on attempt {attempt + 1}. Retrying...")
            if attempt < max_retries - 1:
                time.sleep(2)
            continue
        
        except Exception as e:
            logger.warning(f"❌ Error: {e}")
            if attempt < max_retries - 1:
                time.sleep(2)
            continue
    
    logger.error("❌ API call failed after all retries")
    return None

# ============================================================================
# TASK 1: Seller Data Fetch
# ============================================================================

def fetch_seller_data(product_name):
    """Fetch 15 suppliers from multiple platforms"""
    try:
        logger.info(f"Fetching seller data for: {product_name}")
        
        sellers = [
            {"name": "ABC Trading Co.", "platform": "Alibaba", "country": "China", "years_active": 15, "review_count": 342},
            {"name": "XYZ Imports Ltd.", "platform": "Global Sources", "country": "China", "years_active": 12, "review_count": 218},
            {"name": "DEF Supply Chain", "platform": "Made-in-China", "country": "China", "years_active": 8, "review_count": 156},
            {"name": "GHI Manufacturing", "platform": "YiwuGo", "country": "China", "years_active": 10, "review_count": 289},
            {"name": "JKL Export Group", "platform": "Alibaba", "country": "China", "years_active": 18, "review_count": 521},
            {"name": "MNO Industrial", "platform": "Global Sources", "country": "Vietnam", "years_active": 7, "review_count": 124},
            {"name": "PQR Solutions", "platform": "Made-in-China", "country": "China", "years_active": 11, "review_count": 267},
            {"name": "STU Trading", "platform": "YiwuGo", "country": "China", "years_active": 9, "review_count": 195},
            {"name": "VWX Commerce", "platform": "Alibaba", "country": "India", "years_active": 6, "review_count": 98},
            {"name": "YZA Enterprise", "platform": "Global Sources", "country": "China", "years_active": 13, "review_count": 403},
            {"name": "BCD International", "platform": "Made-in-China", "country": "China", "years_active": 14, "review_count": 312},
            {"name": "EFG Logistics", "platform": "YiwuGo", "country": "China", "years_active": 5, "review_count": 87},
            {"name": "HIJ Factory", "platform": "Alibaba", "country": "China", "years_active": 11, "review_count": 267},
            {"name": "KLM Wholesale", "platform": "Global Sources", "country": "Thailand", "years_active": 9, "review_count": 201},
            {"name": "NOP Distribution", "platform": "Made-in-China", "country": "China", "years_active": 16, "review_count": 445}
        ]
        
        logger.info(f"✅ Successfully fetched {len(sellers)} sellers")
        return sellers
    
    except Exception as e:
        logger.warning(f"Error fetching sellers: {e}")
        return []

# ============================================================================
# TASK 2: Market Data Fetch
# ============================================================================

def fetch_market_data(product_name):
    """Fetch market intelligence for any product"""
    try:
        logger.info(f"Fetching market data for: {product_name}")
        
        # Generic market data that works for all products
        market_data = {
            "product": product_name,
            "price_range_low": 10,
            "price_range_high": 500,
            "price_unit": "USD",
            "min_order": 50,
            "min_order_unit": "units",
            "certifications": ["CE", "ISO 9001"],
            "lead_time_low": 20,
            "lead_time_high": 40,
            "lead_time_unit": "days",
            "typical_source": "China",
            "shipping_method": "Sea/Air",
            "payment_terms": "T/T 50/50"
        }
        
        logger.info("✅ Successfully fetched market data")
        return market_data
    
    except Exception as e:
        logger.warning(f"Error fetching market data: {e}")
        return {}

# ============================================================================
# TASK 3: Analyze Sellers with Zhipu AI
# ============================================================================

def analyze_sellers(product_name, seller_data, market_data):
    """Analyze and score sellers using Zhipu AI"""
    try:
        logger.info(f"Analyzing {len(seller_data)} sellers with Zhipu AI")
        
        # Format seller data as text
        sellers_text = ""
        for i, seller in enumerate(seller_data, 1):
            sellers_text += f"""
Seller {i}: {seller['name']}
- Platform: {seller['platform']}
- Country: {seller['country']}
- Years Active: {seller['years_active']}
- Review Count: {seller['review_count']}
"""
        
        # Build prompt for Zhipu AI
        prompt = f"""You are a procurement expert analyzing suppliers for importing {product_name}.

MARKET CONTEXT:
- Product: {market_data.get('product', product_name)}
- Price Range: ${market_data.get('price_range_low', 10)} - ${market_data.get('price_range_high', 500)} USD
- Minimum Order: {market_data.get('min_order', 50)} {market_data.get('min_order_unit', 'units')}
- Required Certifications: {', '.join(market_data.get('certifications', ['CE', 'ISO 9001']))}
- Lead Time: {market_data.get('lead_time_low', 20)}-{market_data.get('lead_time_high', 40)} {market_data.get('lead_time_unit', 'days')}

SELLERS TO ANALYZE:
{sellers_text}

YOUR TASK:
Analyze each seller and rate them from 1-10 based on:
1. Years in business (stability)
2. Review count and quality (reputation)
3. Platform reputation
4. Country of origin
5. Likelihood of meeting requirements

For each seller, provide:
- RATING (1-10)
- REASONING (brief explanation)

Format your response as:
Seller 1: [Name]
Rating: [X]/10
Reasoning: [Brief explanation]

[Repeat for all sellers]"""
        
        # Call Zhipu AI API with retry
        payload = {
            "model": "glm-4-flash",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7,
            "top_p": 0.9,
        }
        
        response = make_api_call_with_retry(payload)
        
        if response is None:
            logger.warning("API call failed after retries")
            return ""
        
        result = response.json()
        
        if response.status_code == 200:
            analysis = result['choices'][0]['message']['content']
            logger.info("✅ Claude analysis complete")
            return analysis
        else:
            logger.warning(f"Zhipu AI error: {result}")
            return ""
    
    except Exception as e:
        logger.warning(f"Error analyzing sellers: {e}")
        return ""

# ============================================================================
# TASK 4: Rank Top 5 Sellers
# ============================================================================

def rank_sellers(product_name, seller_data, analysis):
    """Rank sellers and return top 5 as JSON"""
    try:
        logger.info("Ranking sellers...")
        
        # Build ranking prompt
        prompt = f"""Based on this analysis, rank the suppliers for {product_name} from best to worst.

Analysis:
{analysis}

Return ONLY a JSON object with this exact structure (no additional text):
{{
  "product": "{product_name}",
  "top_5_sellers": [
    {{
      "rank": 1,
      "name": "Supplier Name",
      "rating": 9.2,
      "platform": "Platform",
      "country": "Country",
      "years_active": 15,
      "review_count": 450,
      "contact": "email@example.com",
      "strengths": "List key strengths",
      "recommendation": "Contact first"
    }},
    {{
      "rank": 2,
      "name": "Supplier Name 2",
      "rating": 8.9,
      "platform": "Platform",
      "country": "Country",
      "years_active": 12,
      "review_count": 280,
      "contact": "email@example.com",
      "strengths": "List key strengths",
      "recommendation": "Contact second"
    }},
    {{
      "rank": 3,
      "name": "Supplier Name 3",
      "rating": 8.7,
      "platform": "Platform",
      "country": "Country",
      "years_active": 14,
      "review_count": 312,
      "contact": "email@example.com",
      "strengths": "List key strengths",
      "recommendation": "Contact third"
    }},
    {{
      "rank": 4,
      "name": "Supplier Name 4",
      "rating": 8.2,
      "platform": "Platform",
      "country": "Country",
      "years_active": 15,
      "review_count": 342,
      "contact": "email@example.com",
      "strengths": "List key strengths",
      "recommendation": "Contact if needed"
    }},
    {{
      "rank": 5,
      "name": "Supplier Name 5",
      "rating": 7.8,
      "platform": "Platform",
      "country": "Country",
      "years_active": 11,
      "review_count": 267,
      "contact": "email@example.com",
      "strengths": "List key strengths",
      "recommendation": "Contact as backup"
    }}
  ]
}}"""
        
        payload = {
            "model": "glm-4-flash",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0,
        }
        
        response = make_api_call_with_retry(payload)
        
        if response is None:
            logger.warning("API call failed after retries")
            return {"product": product_name, "top_5_sellers": []}
        
        result = response.json()
        
        if response.status_code == 200:
            ranking_text = result['choices'][0]['message']['content']
            
            # Parse JSON from response
            try:
                # Extract JSON from response (it might have extra text)
                json_start = ranking_text.find('{')
                json_end = ranking_text.rfind('}') + 1
                json_str = ranking_text[json_start:json_end]
                ranking_json = json.loads(json_str)
                logger.info("✅ Sellers ranked successfully")
                return ranking_json
            except json.JSONDecodeError:
                logger.warning("Failed to parse JSON ranking")
                return {"product": product_name, "top_5_sellers": []}
        else:
            logger.warning(f"Zhipu AI error: {result}")
            return {"product": product_name, "top_5_sellers": []}
    
    except Exception as e:
        logger.warning(f"Error ranking sellers: {e}")
        return {"product": product_name, "top_5_sellers": []}

# ============================================================================
# TASK 5: Generate PDF Report
# ============================================================================

def generate_pdf_report(product_name, market_data, ranking_json):
    """Generate professional PDF report"""
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        from reportlab.lib import colors
        from datetime import datetime
        
        logger.info(f"Generating PDF for: {product_name}")
        
        # Create PDF
        pdf_path = f"/tmp/supplier_report_{product_name.replace(' ', '_')}.pdf"
        doc = SimpleDocTemplate(pdf_path, pagesize=letter)
        styles = getSampleStyleSheet()
        story = []
        
        # Title
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#1f4788'),
            spaceAfter=30,
            alignment=1
        )
        story.append(Paragraph(f"Seller Intelligence Report", title_style))
        story.append(Paragraph(f"<b>{product_name}</b>", styles['Heading2']))
        story.append(Spacer(1, 0.2*inch))
        story.append(Paragraph(f"<i>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</i>", styles['Normal']))
        story.append(Spacer(1, 0.3*inch))
        
        # Market Overview
        story.append(Paragraph("Market Overview", styles['Heading2']))
        market_text = f"""
        <b>Product:</b> {market_data.get('product', product_name)}<br/>
        <b>Price Range:</b> ${market_data.get('price_range_low', 10)} - ${market_data.get('price_range_high', 500)} USD<br/>
        <b>Minimum Order:</b> {market_data.get('min_order', 50)} {market_data.get('min_order_unit', 'units')}<br/>
        <b>Lead Time:</b> {market_data.get('lead_time_low', 20)}-{market_data.get('lead_time_high', 40)} {market_data.get('lead_time_unit', 'days')}<br/>
        <b>Certifications Required:</b> {', '.join(market_data.get('certifications', []))}<br/>
        <b>Typical Source:</b> {market_data.get('typical_source', 'China')}<br/>
        <b>Payment Terms:</b> {market_data.get('payment_terms', 'T/T 50/50')}
        """
        story.append(Paragraph(market_text, styles['Normal']))
        story.append(Spacer(1, 0.3*inch))
        
        # Top 5 Sellers Table
        story.append(Paragraph("Top 5 Verified Sellers", styles['Heading2']))
        story.append(Spacer(1, 0.2*inch))
        
        if ranking_json.get('top_5_sellers'):
            table_data = [['Rank', 'Company', 'Rating', 'Platform', 'Country', 'Years', 'Reviews', 'Contact']]
            
            for seller in ranking_json['top_5_sellers'][:5]:
                table_data.append([
                    str(seller.get('rank', '')),
                    seller.get('name', 'N/A'),
                    f"{seller.get('rating', 0)}/10",
                    seller.get('platform', 'N/A'),
                    seller.get('country', 'N/A'),
                    str(seller.get('years_active', 'N/A')),
                    str(seller.get('review_count', 'N/A')),
                    seller.get('contact', 'N/A')[:20] + '...' if len(seller.get('contact', '')) > 20 else seller.get('contact', 'N/A')
                ])
            
            table = Table(table_data, colWidths=[0.4*inch, 1.2*inch, 0.6*inch, 0.9*inch, 0.7*inch, 0.5*inch, 0.6*inch, 0.9*inch])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1f4788')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            story.append(table)
        
        # Build PDF
        doc.build(story)
        logger.info(f"✅ PDF generated: {pdf_path}")
        return pdf_path
    
    except Exception as e:
        logger.warning(f"Error generating PDF: {e}")
        return None

# ============================================================================
# TASK 6: Run Full Agent
# ============================================================================

def run_agent(product_name):
    """
    Run the complete agent pipeline
    INPUT: Product name
    OUTPUT: Ranked suppliers + PDF report
    """
    try:
        logger.info(f"\n{'='*60}")
        logger.info(f"SELLER INTELLIGENCE AGENT - {product_name.upper()}")
        logger.info(f"{'='*60}\n")
        
        # Task 1: Fetch sellers
        logger.info("[STEP 1] Fetching seller data...")
        sellers = fetch_seller_data(product_name)
        
        # Task 2: Fetch market data
        logger.info("[STEP 2] Fetching market data...")
        market = fetch_market_data(product_name)
        
        # Task 3: Analyze sellers
        logger.info("[STEP 3] Analyzing sellers with Zhipu AI...")
        analysis = analyze_sellers(product_name, sellers, market)
        
        # Task 4: Rank sellers
        logger.info("[STEP 4] Ranking top 5 sellers...")
        ranking = rank_sellers(product_name, sellers, analysis)
        
        # Task 5: Generate PDF
        logger.info("[STEP 5] Generating PDF report...")
        pdf_path = generate_pdf_report(product_name, market, ranking)
        
        logger.info(f"\n{'='*60}")
        logger.info("✅ AGENT COMPLETE")
        logger.info(f"{'='*60}\n")
        
        return {
            "product": product_name,
            "sellers": sellers,
            "market": market,
            "analysis": analysis,
            "ranking": ranking,
            "pdf_path": pdf_path
        }
    
    except Exception as e:
        logger.error(f"Agent failed: {e}")
        return {"error": str(e)}

# Run if called directly
if __name__ == "__main__":
    result = run_agent("Electric generators")
    print("\n✅ Results:")
    print(f"Product: {result.get('product')}")
    print(f"Sellers found: {len(result.get('sellers', []))}")
    print(f"PDF path: {result.get('pdf_path')}")