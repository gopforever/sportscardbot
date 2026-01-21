"""Streamlit Dashboard for Sports Card Bot"""

import os
import sys
from pathlib import Path
import streamlit as st
import pandas as pd
import yaml
from dotenv import load_dotenv
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.ebay_client import eBayClient
from src.price_analyzer import PriceAnalyzer
from src.utils import format_currency, logger

# Page configuration
st.set_page_config(
    page_title="Sports Card Bot",
    page_icon="🏀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Load environment variables
load_dotenv()

# Load configuration
@st.cache_resource
def load_config():
    """Load configuration from YAML file"""
    config_path = Path(__file__).parent / "config.yaml"
    if not config_path.exists():
        st.error("config.yaml not found!")
        return {}
    
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)

config = load_config()

# Initialize session state
if 'opportunities' not in st.session_state:
    st.session_state.opportunities = {}
if 'last_search' not in st.session_state:
    st.session_state.last_search = None
if 'search_history' not in st.session_state:
    st.session_state.search_history = []

# Initialize clients
@st.cache_resource
def init_clients(discount_threshold, min_samples, recency_weight):
    """Initialize eBay client and price analyzer"""
    app_id = os.getenv('EBAY_APP_ID')
    
    if not app_id or app_id == 'your_app_id_here':
        st.error("⚠️ eBay API credentials not configured!")
        st.info("""
        **Setup Instructions:**
        1. Get API keys from https://developer.ebay.com/my/keys
        2. Copy `.env.example` to `.env`
        3. Add your `EBAY_APP_ID` to `.env`
        4. Restart the app
        """)
        st.stop()
    
    try:
        ebay_client = eBayClient(app_id)
        price_analyzer = PriceAnalyzer(
            discount_threshold=discount_threshold,
            min_sold_samples=min_samples,
            recency_weight=recency_weight
        )
        return ebay_client, price_analyzer
    except Exception as e:
        st.error(f"Failed to initialize clients: {str(e)}")
        st.stop()

# Sidebar configuration
st.sidebar.title("🏀 Sports Card Bot")
st.sidebar.markdown("Find underpriced sports cards on eBay")

st.sidebar.markdown("---")
st.sidebar.subheader("Search Configuration")

# Search keywords
keywords_input = st.sidebar.text_area(
    "Search Keywords (one per line)",
    value="\n".join(config.get('search', {}).get('keywords', [])),
    height=100,
    help="Enter one search term per line"
)
keywords = [k.strip() for k in keywords_input.split('\n') if k.strip()]

# Analysis settings
st.sidebar.subheader("Analysis Settings")
discount_threshold = st.sidebar.slider(
    "Discount Threshold (%)",
    min_value=5,
    max_value=50,
    value=config.get('analysis', {}).get('discount_threshold', 20),
    help="Minimum discount to flag as opportunity"
)

sold_days = st.sidebar.slider(
    "Days of Sold Data",
    min_value=7,
    max_value=90,
    value=config.get('analysis', {}).get('sold_days', 30),
    help="How far back to look for sold listings"
)

min_samples = st.sidebar.slider(
    "Min Sold Samples",
    min_value=3,
    max_value=20,
    value=config.get('analysis', {}).get('min_sold_samples', 5),
    help="Minimum sold listings needed for analysis"
)

# Price filters
st.sidebar.subheader("Price Filters")
col1, col2 = st.sidebar.columns(2)
min_price = col1.number_input(
    "Min Price ($)",
    min_value=0,
    value=config.get('filters', {}).get('min_price', 10),
    step=10
)
max_price = col2.number_input(
    "Max Price ($)",
    min_value=0,
    value=config.get('filters', {}).get('max_price', 1000),
    step=50
)

# Condition filter
condition = st.sidebar.selectbox(
    "Condition",
    options=["All", "New", "Used", "Not Specified"],
    index=0
)
condition_filter = None if condition == "All" else condition

# Listing type
listing_type = st.sidebar.selectbox(
    "Listing Type",
    options=["all", "auction", "fixed"],
    index=0
)

# Search button
st.sidebar.markdown("---")
search_button = st.sidebar.button("🔍 Search for Deals", type="primary", use_container_width=True)

# Main content
st.title("🏀 Sports Card Deal Finder")
st.markdown("Discover underpriced sports cards by comparing active listings to recent sold prices")

# Initialize clients with current settings
ebay_client, price_analyzer = init_clients(discount_threshold, min_samples, 0.7)

# Update config with current settings
config['analysis']['discount_threshold'] = discount_threshold
config['analysis']['sold_days'] = sold_days
config['analysis']['min_sold_samples'] = min_samples
config['filters']['min_price'] = min_price
config['filters']['max_price'] = max_price
config['filters']['condition'] = condition_filter
config['search']['listing_type'] = listing_type

# Search logic
if search_button:
    if not keywords:
        st.warning("Please enter at least one search keyword")
    else:
        with st.spinner("Searching eBay and analyzing prices..."):
            try:
                # Run analysis
                results = price_analyzer.analyze_by_keyword(keywords, ebay_client, config)
                
                # Store results
                st.session_state.opportunities = results
                st.session_state.last_search = datetime.now()
                
                if results:
                    st.session_state.search_history.append({
                        'timestamp': datetime.now(),
                        'keywords': keywords,
                        'deals_found': sum(len(df) for df in results.values())
                    })
                
                st.success(f"Search completed! Found opportunities for {len(results)} keywords")
                
            except Exception as e:
                st.error(f"Search failed: {str(e)}")
                logger.error(f"Search error: {str(e)}")

# Display results
if st.session_state.opportunities:
    # Combine all opportunities
    all_opportunities = pd.concat(
        st.session_state.opportunities.values(),
        ignore_index=True
    )
    
    # Summary metrics
    st.markdown("### 📊 Summary")
    col1, col2, col3, col4 = st.columns(4)
    
    stats = price_analyzer.get_summary_stats(all_opportunities)
    
    col1.metric("Total Deals", stats['total_deals'])
    col2.metric("Avg Discount", f"{stats['avg_discount']:.1f}%")
    col3.metric("Avg Profit", format_currency(stats['avg_potential_profit']))
    col4.metric("Total Profit Potential", format_currency(stats['total_potential_profit']))
    
    # Charts
    st.markdown("### 📈 Analytics")
    chart_col1, chart_col2 = st.columns(2)
    
    with chart_col1:
        # Discount distribution
        fig_discount = px.histogram(
            all_opportunities,
            x='discount_pct',
            nbins=20,
            title='Discount Distribution',
            labels={'discount_pct': 'Discount %', 'count': 'Number of Deals'}
        )
        st.plotly_chart(fig_discount, use_container_width=True)
    
    with chart_col2:
        # Profit potential distribution
        fig_profit = px.histogram(
            all_opportunities,
            x='potential_profit',
            nbins=20,
            title='Profit Potential Distribution',
            labels={'potential_profit': 'Potential Profit ($)', 'count': 'Number of Deals'}
        )
        st.plotly_chart(fig_profit, use_container_width=True)
    
    # Opportunities table
    st.markdown("### 🎯 Opportunities")
    
    # Filter options
    filter_col1, filter_col2, filter_col3 = st.columns(3)
    with filter_col1:
        sort_by = st.selectbox(
            "Sort by",
            options=['discount_pct', 'potential_profit', 'active_price'],
            format_func=lambda x: {
                'discount_pct': 'Discount %',
                'potential_profit': 'Profit Potential',
                'active_price': 'Price'
            }[x]
        )
    
    with filter_col2:
        max_discount_value = int(all_opportunities['discount_pct'].max()) if not all_opportunities.empty else 100
        min_discount_filter = st.slider(
            "Min Discount (%)",
            min_value=0,
            max_value=max_discount_value,
            value=0
        )
    
    with filter_col3:
        search_text = st.text_input("Search in titles", "")
    
    # Apply filters
    filtered_df = all_opportunities.copy()
    if min_discount_filter > 0:
        filtered_df = filtered_df[filtered_df['discount_pct'] >= min_discount_filter]
    if search_text:
        filtered_df = filtered_df[
            filtered_df['title'].str.contains(search_text, case=False, na=False)
        ]
    
    # Sort
    filtered_df = filtered_df.sort_values(sort_by, ascending=False)
    
    st.info(f"Showing {len(filtered_df)} of {len(all_opportunities)} opportunities")
    
    # Display cards
    for idx, row in filtered_df.iterrows():
        with st.expander(f"**{row['title'][:80]}...** - {row['discount_pct']:.1f}% off"):
            card_col1, card_col2 = st.columns([1, 2])
            
            with card_col1:
                if row['image_url']:
                    try:
                        st.image(row['image_url'], use_container_width=True)
                    except Exception:
                        st.info("Image not available")
                else:
                    st.info("No image")
            
            with card_col2:
                st.markdown(f"**Full Title:** {row['title']}")
                st.markdown(f"**Condition:** {row['condition']}")
                st.markdown(f"**Seller:** {row['seller']}")
                st.markdown(f"**Listing Type:** {row['listing_type']}")
                
                metric_col1, metric_col2, metric_col3 = st.columns(3)
                metric_col1.metric("Active Price", format_currency(row['active_price']))
                metric_col2.metric("Market Value", format_currency(row['market_value']))
                metric_col3.metric("Potential Profit", format_currency(row['potential_profit']))
                
                metric_col4, metric_col5, metric_col6 = st.columns(3)
                metric_col4.metric("Discount", f"{row['discount_pct']:.1f}%")
                metric_col5.metric("Profit Margin", f"{row['profit_margin']:.1f}%")
                metric_col6.metric("Sold Comps", int(row['sold_comps']))
                
                st.markdown(f"[🔗 View on eBay]({row['url']})")
    
    # Export button
    st.markdown("---")
    csv = filtered_df.to_csv(index=False)
    st.download_button(
        label="📥 Export to CSV",
        data=csv,
        file_name=f"sports_card_deals_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        mime="text/csv",
        use_container_width=True
    )

else:
    # Welcome screen
    st.info("👆 Configure your search in the sidebar and click 'Search for Deals' to get started!")
    
    st.markdown("### 🚀 How It Works")
    st.markdown("""
    1. **Configure** your search keywords and filters in the sidebar
    2. **Click** the 'Search for Deals' button
    3. **Review** the opportunities sorted by discount percentage
    4. **Export** results to CSV for further analysis
    """)
    
    st.markdown("### 🎯 Features")
    cols = st.columns(3)
    with cols[0]:
        st.markdown("**📊 Price Analysis**")
        st.markdown("Compares active listings against recent sold data")
    with cols[1]:
        st.markdown("**🔍 Smart Filtering**")
        st.markdown("Filter by price, condition, and listing type")
    with cols[2]:
        st.markdown("**💰 Profit Calculator**")
        st.markdown("Calculates potential profit and margins")
    
    st.markdown("### ⚙️ Configuration")
    st.markdown("""
    Customize your search parameters:
    - **Discount Threshold**: Minimum discount to flag as opportunity
    - **Sold Days**: How far back to analyze sold listings
    - **Min Samples**: Minimum sold comps for reliable data
    - **Price Range**: Focus on specific price ranges
    """)

# Footer
st.sidebar.markdown("---")
st.sidebar.markdown("### 📝 About")
st.sidebar.info("""
**Sports Card Bot v1.0**

Finds underpriced sports cards on eBay by comparing active listings to market value.

[📚 Documentation](README.md)
""")

if st.session_state.last_search:
    st.sidebar.markdown(f"Last search: {st.session_state.last_search.strftime('%I:%M %p')}")
