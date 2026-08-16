import streamlit as st
from seller_agent import run_agent
import json
from datetime import datetime

st.set_page_config(
    page_title="Dealbaku - Supplier Intelligence",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
    <style>
    .header {
        background: linear-gradient(135deg, #1f4788 0%, #2d5fa8 100%);
        padding: 30px;
        border-radius: 10px;
        color: white;
        margin-bottom: 30px;
    }
    .supplier-card {
        background: linear-gradient(135deg, #ffffff 0%, #f8f9fa 100%);
        padding: 20px;
        border-radius: 8px;
        border-left: 4px solid #1f4788;
        margin-bottom: 15px;
    }
    </style>
""", unsafe_allow_html=True)

st.markdown("""
    <div class="header">
    <h1>🔍 Dealbaku</h1>
    <p>AI-Powered Supplier Intelligence Platform</p>
    <small>Find verified suppliers with market analysis in seconds</small>
    </div>
""", unsafe_allow_html=True)

tab1, tab2 = st.tabs(["🔍 Search Suppliers", "📊 About"])

with tab1:
    col1, col2 = st.columns([3, 1])
    
    with col1:
        product_query = st.text_input(
            "Search for suppliers:",
            placeholder="e.g., LED lights, Electric generators, Textiles, Industrial machinery",
            key="product_search"
        )
    
    with col2:
        search_button = st.button("🔍 Search", use_container_width=True)
    
    if search_button and product_query:
        st.session_state.last_search = product_query
        
        with st.spinner(f"🔍 Analyzing {product_query}..."):
            result = run_agent(product_query)
        
        if "error" not in result:
            st.success(f"✅ Analysis complete for **{product_query}**")
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Database Size", result.get('total_database', 0))
            with col2:
                st.metric("Relevant Suppliers", result.get('relevant_suppliers', 0))
            with col3:
                st.metric("Top Ranked", len(result.get('top_5', [])))
            with col4:
                st.metric("Analysis Time", "2-3 min")
            
            st.divider()
            
            st.subheader("📈 Market Intelligence")
            market = result.get('market_data', {})
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.info(f"💰 **Price Range**\n${market.get('price_range_low', 'N/A')}-${market.get('price_range_high', 'N/A')}")
            with col2:
                st.info(f"📦 **Min Order**\n{market.get('min_order', 'N/A')} {market.get('min_order_unit', 'units')}")
            with col3:
                st.info(f"⏱️ **Lead Time**\n{market.get('lead_time_low', 'N/A')}-{market.get('lead_time_high', 'N/A')} days")
            with col4:
                st.info(f"✅ **Certifications**\n{', '.join(market.get('certifications', []))}")
            
            st.divider()
            
            st.subheader("🏆 Top 5 Verified Suppliers")
            
            for idx, supplier in enumerate(result.get('top_5', []), 1):
                with st.container():
                    col1, col2, col3 = st.columns([2, 2, 1])
                    
                    with col1:
                        st.markdown(f"### #{idx} {supplier.get('name', 'N/A')}")
                    
                    with col2:
                        rating = supplier.get('rating', 0)
                        stars = "⭐" * int(rating) + ("✨" if rating % 1 >= 0.5 else "")
                        st.markdown(f"**{rating}/5.0** {stars}")
                    
                    with col3:
                        relevance = supplier.get('relevance_score', 0)
                        st.markdown(f"📊 **Relevance: {relevance:.0f}%**")
                    
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.write(f"📍 {supplier.get('city', 'N/A')}, {supplier.get('country', 'N/A')}")
                    with col2:
                        st.write(f"🏢 {supplier.get('platform', 'N/A')}")
                    with col3:
                        st.write(f"⏱️ {supplier.get('years_active', 'N/A')} yrs active")
                    with col4:
                        st.write(f"⭐ {supplier.get('review_count', 'N/A')} reviews")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write(f"📧 {supplier.get('email', 'N/A')}")
                    with col2:
                        st.write(f"📱 {supplier.get('phone', 'N/A')}")
                    
                    if supplier.get('wechat'):
                        st.write(f"💬 WeChat: `{supplier.get('wechat')}`")
                    
                    if supplier.get('ai_score'):
                        st.write(f"🤖 AI Score: **{supplier.get('ai_score')}/10** - {supplier.get('key_strength', 'Strong supplier')}")
                    
                    st.divider()
            
            st.download_button(
                label="📥 Export as JSON",
                data=json.dumps(result, indent=2),
                file_name=f"dealbaku_{product_query.replace(' ', '_')}.json",
                mime="application/json",
                use_container_width=True
            )
        
        else:
            st.error(f"❌ Error: {result.get('error')}")
    
    elif search_button:
        st.warning("⚠️ Please enter a product name")

with tab2:
    st.markdown("""
    ## About Dealbaku
    
    Dealbaku is an **AI-powered supplier intelligence platform** that helps importers and traders 
    find verified suppliers from B2B marketplaces in minutes.
    
    ### Features
    - 🔍 Smart Supplier Filtering - AI analyzes 15+ suppliers
    - 📊 Market Intelligence - Real pricing, certifications, lead times
    - 🤖 AI Ranking - Zhipu GLM-4 analyzes by product relevance
    - ✅ Verified Data - Suppliers with 5-18+ years in business
    - 📥 Export Results - Download as JSON
    
    ### Supported Platforms
    - Alibaba, Global Sources, Made-in-China, YiwuGo
    
    ### Use Cases
    - Finding manufacturers for bulk orders
    - Sourcing components
    - International trade & import-export
    - Supply chain optimization
    
    **Version**: 2.0 (Zhipu AI Enhanced)  
    Made with ❤️ for international traders
    """)

st.markdown("---")
st.markdown("""
    <div style="text-align: center; color: #999; font-size: 12px; padding: 20px;">
    🚀 <b>Dealbaku</b> | AI Supplier Intelligence | Powered by Zhipu AI
    </div>
""", unsafe_allow_html=True)