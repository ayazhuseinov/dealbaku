# Dealbaku

AI-powered supplier discovery and supply chain intelligence platform.

## Overview
Dealbaku helps traders, importers, and businesses worldwide discover, analyze, and evaluate suppliers using AI-driven insights. Whether you're sourcing from China for the USA, Europe, or anywhere globally, Dealbaku accelerates your sourcing process with data-driven decision making.

## Features
- **Supplier Intelligence**: Analyze supplier credibility, pricing, and reliability
- **Market Analysis**: Real-time market trends and competitive positioning
- **Deal Evaluation**: AI-powered scoring of trade opportunities
- **Global Sourcing**: Works for any product, any market, any country

## Tech Stack
- Python 3.8+
- Zhipu GLM API (LLM)
- Streamlit (Web UI)
- Pandas (Data Analysis)
- SQLite (Database)

## Usage

```bash
streamlit run streamlit_app.py
```

Input your product category, target location, and constraints to get AI-powered supplier analysis.

## Supplier Finder (CLI)

Data-driven supplier discovery on 1688: hard constraints in, percentile-ranked
shortlist and a GLM-5.3 brief out. No fixed thresholds: "top quartile" is
computed from whatever the search returns.

```bash
pip install -r requirements.txt
cp .env.example .env   # add NVIDIA_API_KEY and ALIBABA_1688_API_KEY

python main.py --product "dog beds" --location "Guangdong" --moq 500 \
    --platform gold_supplier          # or verified_badge | any
```

Keys can also be passed with `--1688-key` / `--nvidia-key`.

Pipeline (`suppliers/`, `reports/`):

1. **search_1688.py**: fetch every result page, merge listings per seller, keep
   suppliers in the location with MOQ ≤ limit and the required badge
2. **distribution.py**: min / max / median / 75th percentile for years,
   rating and reviews, plus market price min / max / average / median
3. **ranking.py**: `(value - min) / (max - min) * 100` per metric, weighted
   years 25% · rating 35% · reviews 25% + badge bonus (gold +10, verified +5)
4. **extraction.py**: fill missing WeChat / phone / email from the store page,
   otherwise mark "not publicly listed"
5. **analysis.py**: GLM-5.3 (NVIDIA endpoint) assesses the top 5
6. **reports/generator.py**: console brief + `dealbaku_supplier_analysis_<product>_<date>.json` / `.txt`

If the 1688 API fails you are prompted for a JSON/CSV export instead; pass it
directly with `--suppliers-file`. Try it offline with the synthetic demo data:

```bash
python main.py --product "dog beds" --location Guangdong --moq 500 \
    --platform gold_supplier --suppliers-file data/sample_suppliers_dog_beds.json \
    --skip-glm --no-scrape
```

The 1688 client targets a data gateway (default OneBound `item_search`; set
`ALIBABA_1688_API_URL`) and accepts the common field names, English or Chinese.

Tests: `python -m pytest`

## Project Status
**v0.2 - AI Supplier Intelligence**
- ✅ Supplier discovery & ranking
- ✅ Market research integration
- 🔄 Real 1688 API integration (coming)
- 🔄 Advanced risk modeling

## Author
Ayaz Huseinov  
AI Engineer | International Business (Shanghai University)  
Focus: Global Trade Intelligence & Supply Chain Optimization

## License
MIT
