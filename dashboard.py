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
from src.sportscardpro_client import SportsCardProClient
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
def init_clients(discount_threshold, min_samples, recency_weight, api_source):
    """Initialize API client and price analyzer"""
    
    # Determine which API to use
    use_sportscardpro = api_source == 'sportscardpro'
    
    if use_sportscardpro:
        # Use Sports Card Pro API
        api_key = os.getenv('SPORTSCARDPRO_API_KEY')
        
        if not api_key or api_key == 'your_api_key_here':
            st.error("⚠️ Sports Card Pro API credentials not configured!")
            st.info("""
            **Setup Instructions:**
            1. Visit https://www.sportscardspro.com/api-documentation
            2. Sign up for API access
            3. Get your API key
            4. Copy `.env.example` to `.env`
            5. Add your `SPORTSCARDPRO_API_KEY` to `.env`
            6. Restart the app
            """)
            st.stop()
        
        try:
            client = SportsCardProClient(api_key)
            price_analyzer = PriceAnalyzer(
                discount_threshold=discount_threshold,
                min_sold_samples=min_samples,
                recency_weight=recency_weight
            )
            return client, price_analyzer
        except Exception as e:
            st.error(f"Failed to initialize Sports Card Pro client: {str(e)}")
            st.stop()
    else:
        # Use eBay API (legacy)
        app_id = os.getenv('EBAY_APP_ID')
        environment = os.getenv('EBAY_ENVIRONMENT', 'sandbox').lower()
        
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
            client = eBayClient(app_id, environment=environment)
            price_analyzer = PriceAnalyzer(
                discount_threshold=discount_threshold,
                min_sold_samples=min_samples,
                recency_weight=recency_weight
            )
            return client, price_analyzer
        except Exception as e:
            st.error(f"Failed to initialize eBay client: {str(e)}")
            st.stop()

# Sidebar configuration
st.sidebar.title("🏀 Sports Card Bot")
st.sidebar.markdown("Find underpriced sports cards")

# API Source Selection
st.sidebar.subheader("API Source")
api_source = st.sidebar.radio(
    "Data Source",
    options=['sportscardpro', 'ebay'],
    format_func=lambda x: {
        'sportscardpro': '🎯 Sports Card Pro (Recommended)',
        'ebay': '📦 eBay (Legacy)'
    }[x],
    help="Sports Card Pro provides better sports card-specific data and pricing"
)

# Display environment indicator for eBay
if api_source == 'ebay':
    environment = os.getenv('EBAY_ENVIRONMENT', 'sandbox').lower()
    st.sidebar.info(f"🌐 Environment: **{environment.upper()}**")
    
    if environment == 'sandbox':
        st.sidebar.warning("⚠️ Using sandbox (test) data. Switch to production for real listings.")
    else:
        st.sidebar.success("✅ Using production (real) data.")
else:
    st.sidebar.success("✅ Using Sports Card Pro API")

# eBay Web Scraping Option (only for Sports Card Pro mode)
use_ebay_scraping = False
ebay_scraper = None
if api_source == 'sportscardpro':
    st.sidebar.markdown("---")
    use_ebay_scraping = st.sidebar.checkbox(
        "Enable eBay Scraping",
        value=False,
        help="Scrape eBay for current listings and compare to Sports Card Pro market values"
    )
    
    if use_ebay_scraping:
        st.sidebar.info("⚠️ Web scraping is for personal use only. Be respectful of eBay's servers.")
        # Initialize scraper
        from src.ebay_scraper import eBayScraper
        ebay_scraper = eBayScraper(delay_between_requests=2.0)

st.sidebar.markdown("---")
st.sidebar.subheader("Search Configuration")

# Search keywords or filters based on API source
if api_source == 'sportscardpro':
    # Sports Card Pro specific filters
    search_config = config.get('search', {})
    
    sport = st.sidebar.selectbox(
        "Sport",
        options=['', 'Baseball', 'Basketball', 'Football', 'Hockey', 'Soccer'],
        help="Filter by sport"
    )
    
    player = st.sidebar.text_input(
        "Player Name",
        value=search_config.get('players', [''])[0] if search_config.get('players') else '',
        help="Search by player name"
    )
    
    year = st.sidebar.text_input(
        "Year",
        value=str(search_config.get('years', [''])[0]) if search_config.get('years') else '',
        help="Card year (e.g., 2023, 1986-87)"
    )
    
    card_set = st.sidebar.text_input(
        "Set",
        value=search_config.get('sets', [''])[0] if search_config.get('sets') else '',
        help="Card set name (e.g., Topps, Fleer)"
    )
    
    # General query field
    query = st.sidebar.text_input(
        "Search Query (optional)",
        value='',
        help="General search query"
    )
    
    # Build keywords list for compatibility
    keywords = []
    if query:
        keywords.append(query)
    elif player:
        keywords.append(player)
    elif sport:
        keywords.append(sport)
    else:
        keywords = ['']  # Empty search will return general results
else:
    # eBay keywords (legacy)
    keywords_input = st.sidebar.text_area(
        "Search Keywords (one per line)",
        value="\n".join(config.get('search', {}).get('keywords', [])),
        height=100,
        help="Enter one search term per line"
    )
    keywords = [k.strip() for k in keywords_input.split('\n') if k.strip()]
    
    # Set empty values for Sports Card Pro filters
    sport = None
    player = None
    year = None
    card_set = None

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

# Condition/Grade filters
if api_source == 'sportscardpro':
    # Grading filters for Sports Card Pro
    grading_company = st.sidebar.selectbox(
        "Grading Company",
        options=['', 'PSA', 'BGS', 'SGC', 'CGC', 'HGA'],
        help="Filter by grading company"
    )
    
    grade = st.sidebar.selectbox(
        "Grade",
        options=['', '10', '9.5', '9', '8.5', '8', '7.5', '7', '6', '5', '4', '3', '2', '1'],
        help="Filter by grade"
    )
    
    condition_filter = None
    listing_type = "all"
else:
    # eBay filters (legacy)
    condition = st.sidebar.selectbox(
        "Condition",
        options=["All", "New", "Used", "Not Specified"],
        index=0
    )
    condition_filter = None if condition == "All" else condition
    
    listing_type = st.sidebar.selectbox(
        "Listing Type",
        options=["all", "auction", "fixed"],
        index=0
    )
    
    grading_company = None
    grade = None

# Search button
st.sidebar.markdown("---")
search_button = st.sidebar.button("🔍 Search for Deals", type="primary", use_container_width=True)

# Main content
st.title("🏀 Sports Card Deal Finder")
st.markdown("Discover underpriced sports cards by comparing active listings to recent sold prices")

# Initialize clients with current settings
client, price_analyzer = init_clients(discount_threshold, min_samples, 0.7, api_source)

# Update config with current settings
config['analysis']['discount_threshold'] = discount_threshold
config['analysis']['sold_days'] = sold_days
config['analysis']['min_sold_samples'] = min_samples
config['filters']['min_price'] = min_price
config['filters']['max_price'] = max_price
config['filters']['condition'] = condition_filter
config['search']['listing_type'] = listing_type

# Add Sports Card Pro specific config
if api_source == 'sportscardpro':
    config['search']['sport'] = sport if sport else None
    config['search']['player'] = player if player else None
    config['search']['year'] = year if year else None
    config['search']['set'] = card_set if card_set else None
    config['filters']['grading_company'] = grading_company if grading_company else None
    config['filters']['grade'] = grade if grade else None

# Search logic
if search_button:
    if not keywords:
        if api_source == 'sportscardpro':
            st.warning("Please enter at least one search parameter (player, sport, query, etc.)")
        else:
            st.warning("Please enter at least one search keyword")
    else:
        search_source = "Sports Card Pro" if api_source == 'sportscardpro' else "eBay"
        if use_ebay_scraping and ebay_scraper:
            search_source += " + eBay Scraping"
        
        with st.spinner(f"Searching {search_source} and analyzing prices..."):
            try:
                # Run analysis based on mode
                if use_ebay_scraping and ebay_scraper and api_source == 'sportscardpro':
                    # Use hybrid approach: Sports Card Pro + eBay scraping
                    results = {}
                    for query in keywords:
                        result = price_analyzer.analyze_with_scraping(
                            sportscardpro_client=client,
                            ebay_scraper=ebay_scraper,
                            query=query
                        )
                        if result.get('opportunities'):
                            results[query] = result
                else:
                    # Use standard approach (Sports Card Pro only or eBay API)
                    results = price_analyzer.analyze_by_keyword(keywords, client, config)
                
                # Store results
                st.session_state.opportunities = results
                st.session_state.last_search = datetime.now()
                
                if results:
                    st.session_state.search_history.append({
                        'timestamp': datetime.now(),
                        'keywords': keywords,
                        'deals_found': sum(len(df) if isinstance(df, pd.DataFrame) else len(df.get('opportunities', [])) for df in results.values())
                    })
                
                st.success(f"Search completed! Found opportunities for {len(results)} keywords")
                
            except Exception as e:
                st.error(f"Search failed: {str(e)}")
                logger.error(f"Search error: {str(e)}")

# Display results
if st.session_state.opportunities:
    # Combine all opportunities - handle both DataFrame and dict formats
    all_opportunities_list = []
    
    for query, result in st.session_state.opportunities.items():
        if isinstance(result, pd.DataFrame):
            # Standard DataFrame format
            all_opportunities_list.append(result)
        elif isinstance(result, dict) and 'opportunities' in result:
            # Scraping format - convert to DataFrame
            opps = result['opportunities']
            if opps:
                # Flatten the nested structure
                flattened = []
                for opp in opps:
                    listing = opp.get('listing', {})
                    market_data = opp.get('market_data', {})
                    
                    flattened.append({
                        'title': listing.get('title', 'Unknown'),
                        'active_price': opp.get('listing_price', 0),
                        'market_value': opp.get('market_value', 0),
                        'avg_sold_price': opp.get('market_value', 0),
                        'median_sold_price': opp.get('market_value', 0),
                        'discount_pct': opp.get('discount_pct', 0),
                        'potential_profit': opp.get('potential_profit', 0),
                        'profit_margin': (opp.get('potential_profit', 0) / opp['listing_price']) * 100 if opp.get('listing_price', 0) > 0 else 0.0,
                        'url': listing.get('url', ''),
                        'image_url': listing.get('image_url', ''),
                        'condition': listing.get('condition', 'Unknown'),
                        'seller': listing.get('marketplace', 'eBay'),
                        'listing_type': 'Buy It Now',
                        'sold_comps': 0,
                        'price_std_dev': 0,
                        'player': market_data.get('player', ''),
                        'sport': market_data.get('sport', ''),
                        'year': market_data.get('year', ''),
                        'set': market_data.get('set', ''),
                        'card_number': market_data.get('card_number', ''),
                        'shipping_cost': listing.get('shipping_cost', 0),
                        'source': 'eBay Scraper'
                    })
                
                if flattened:
                    all_opportunities_list.append(pd.DataFrame(flattened))
    
    if all_opportunities_list:
        all_opportunities = pd.concat(all_opportunities_list, ignore_index=True)
    else:
        all_opportunities = pd.DataFrame()
    
    if all_opportunities.empty:
        st.info("No opportunities found. Try adjusting your search parameters or filters.")
    else:
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
                
                # Display Sports Card Pro specific fields if available
                if 'player' in row and row['player']:
                    st.markdown(f"**Player:** {row['player']}")
                if 'sport' in row and row['sport']:
                    st.markdown(f"**Sport:** {row['sport']}")
                if 'year' in row and row['year']:
                    st.markdown(f"**Year:** {row['year']}")
                if 'set' in row and row['set']:
                    st.markdown(f"**Set:** {row['set']}")
                if 'card_number' in row and row['card_number']:
                    st.markdown(f"**Card #:** {row['card_number']}")
                
                # Display eBay specific fields if available
                if 'seller' in row:
                    st.markdown(f"**Seller:** {row['seller']}")
                if 'listing_type' in row:
                    st.markdown(f"**Listing Type:** {row['listing_type']}")
                
                metric_col1, metric_col2, metric_col3 = st.columns(3)
                metric_col1.metric("Active Price", format_currency(row['active_price']))
                metric_col2.metric("Market Value", format_currency(row['market_value']))
                metric_col3.metric("Potential Profit", format_currency(row['potential_profit']))
                
                metric_col4, metric_col5, metric_col6 = st.columns(3)
                metric_col4.metric("Discount", f"{row['discount_pct']:.1f}%")
                metric_col5.metric("Profit Margin", f"{row['profit_margin']:.1f}%")
                metric_col6.metric("Sold Comps", int(row['sold_comps']))
                
                # Show shipping cost if available (for scraped listings)
                if 'shipping_cost' in row and row['shipping_cost'] > 0:
                    st.caption(f"💰 Shipping: {format_currency(row['shipping_cost'])}")
                
                # Link based on source
                if row['url']:
                    # Check if this is a scraped eBay listing or regular listing
                    if 'source' in row and row['source'] == 'eBay Scraper':
                        link_text = "🔗 View on eBay (Scraped)"
                    elif api_source == 'sportscardpro':
                        link_text = "🔗 View Card"
                    else:
                        link_text = "🔗 View on eBay"
                    st.markdown(f"[{link_text}]({row['url']})")
        
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
    if api_source == 'sportscardpro':
        st.markdown("""
        1. **Select** Sports Card Pro as your data source (recommended)
        2. **Configure** your search by sport, player, year, set, or grade in the sidebar
        3. **Click** the 'Search for Deals' button
        4. **Review** the opportunities with market values from Sports Card Pro
        5. **Export** results to CSV for further analysis
        """)
    else:
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
if api_source == 'sportscardpro':
    st.sidebar.info("""
    **Sports Card Bot v2.0**
    
    Finds underpriced sports cards using Sports Card Pro API for accurate market values and pricing data.
    
    [📚 Documentation](README.md)
    """)
else:
    st.sidebar.info("""
    **Sports Card Bot v1.0 (Legacy)**
    
    Finds underpriced sports cards on eBay by comparing active listings to market value.
    
    [📚 Documentation](README.md)
    """)

if st.session_state.last_search:
    st.sidebar.markdown(f"Last search: {st.session_state.last_search.strftime('%I:%M %p')}")
