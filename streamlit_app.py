import streamlit as st
from seller_agent import run_agent
import os

# Page configuration
st.set_page_config(
    page_title="Seller Intelligence Agent",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
    <style>
    .main-header {
        text-align: center;
        padding: 20px;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 10px;
        color: white;
    }
    .stButton>button {
        width: 100%;
        padding: 12px;
        font-size: 16px;
        font-weight: bold;
    }
    </style>
""", unsafe_allow_html=True)

# Header
st.markdown("""
    <div class="main-header">
    <h1>🔍 Seller Intelligence Agent</h1>
    <p>Find Verified Suppliers in 30 Seconds</p>
    </div>
""", unsafe_allow_html=True)

st.write("")

# Sidebar
with st.sidebar:
    st.header("About This Tool")
    st.write("""
    This AI-powered platform helps traders and importers find the best suppliers from China and Asia.
    
    **How it works:**
    1. Enter any product name
    2. AI searches 4 major B2B platforms
    3. Analyzes 15+ suppliers
    4. Ranks top 5 verified sellers
    5. Download professional PDF report
    
    **Platforms covered:**
    - Alibaba International
    - Global Sources
    - Made-in-China
    - YiwuGo
    """)

# Main content
col1, col2 = st.columns([2, 1], gap="large")

with col1:
    st.subheader("🔎 Search Suppliers")
    product_name = st.text_input(
        "Enter product name:",
        placeholder="e.g., LED lights, Textiles, Machinery",
        key="product_input"
    )

with col2:
    st.subheader("Quick Examples")
    if st.button("⚡ LED Lights"):
        product_name = "LED lights"
    if st.button("⚡ Textiles"):
        product_name = "Textiles"
    if st.button("⚡ Machinery"):
        product_name = "Machinery"

st.write("")

# Search button
if st.button("🚀 Find Suppliers", key="search_btn", use_container_width=True):
    if product_name:
        with st.spinner(f"🔍 Finding suppliers for {product_name}..."):
            result = run_agent(product_name)
            
            if "error" not in result:
                # Display results
                st.success("✅ Suppliers found!")
                st.write("")
                
                # Display top 5 suppliers
                st.subheader(f"Top 5 Suppliers: {product_name}")
                
                if result['ranking'].get('top_5_sellers'):
                    for seller in result['ranking']['top_5_sellers'][:5]:
                        col1, col2, col3 = st.columns([1, 2, 1])
                        
                        with col1:
                            st.metric(f"Rank {seller.get('rank')}", f"{seller.get('rating', 'N/A')}/10")
                        
                        with col2:
                            st.write(f"**{seller.get('name', 'N/A')}**")
                            st.write(f"📍 {seller.get('country', 'N/A')} | ⏱️ {seller.get('years_active', 'N/A')} years | ⭐ {seller.get('review_count', 'N/A')} reviews")
                            st.write(f"Platform: {seller.get('platform', 'N/A')}")
                            st.write(f"📧 {seller.get('contact', 'N/A')}")
                        
                        with col3:
                            st.write(seller.get('recommendation', ''))
                        
                        st.write("---")
                
                # Download PDF
                if result.get('pdf_path') and os.path.exists(result['pdf_path']):
                    with open(result['pdf_path'], 'rb') as pdf_file:
                        st.download_button(
                            label="📥 Download PDF Report",
                            data=pdf_file,
                            file_name=f"suppliers_{product_name.replace(' ', '_')}.pdf",
                            mime="application/pdf",
                            use_container_width=True
                        )
                
                st.write("")
                st.info("💡 **Next step:** Contact the top 3 suppliers to negotiate pricing and delivery terms.")
            
            else:
                st.error(f"❌ Error: {result.get('error')}")
    else:
        st.warning("⚠️ Please enter a product name")

# Footer
st.write("")
st.write("---")
st.write("🚀 **Powered by Zhipu AI GLM-4.7-Flash** | Built for international traders")