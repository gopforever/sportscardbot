# 🏀 Sports Card Bot

A Python-based bot that finds sports cards selling below market value using Sports Card Pro API for accurate pricing data, with an interactive dashboard.

## 🎯 Overview

Sports Card Bot helps collectors and traders discover underpriced sports cards by:
- **Searching** sports cards using Sports Card Pro API (recommended) or eBay listings
- **Analyzing** market values from Sports Card Pro's comprehensive database
- **Identifying** cards listed below market value (potential deals)
- **Displaying** opportunities in an interactive dashboard with detailed analytics

## ✨ Features

### Core Functionality
- 🎯 **Sports Card Pro Integration** - Official Sports Card Pro API for accurate market values
- 📦 **eBay Integration (Legacy)** - Optional eBay Finding API support
- 📊 **Price Analysis** - Calculates market value and identifies underpriced opportunities
- 💰 **Profit Calculator** - Shows potential profit and margins for each opportunity
- 📈 **Interactive Dashboard** - Streamlit-based web interface with charts and filters

### Dashboard Features
- Dual API support: Sports Card Pro (recommended) or eBay (legacy)
- Sports-specific filters: sport, player, year, set, grade, grading company
- Card image thumbnails
- Price comparison metrics (active price vs. market value)
- Filter and search within results
- Export results to CSV
- Real-time analytics charts
- Customizable search parameters

## 🚀 Quick Start

### Prerequisites
- Python 3.8 or higher
- Sports Card Pro API key (recommended) OR eBay Developer account

### 1. Get Sports Card Pro API Key (Recommended)

**Why Sports Card Pro?**
- ✅ Specifically designed for sports cards
- ✅ Provides actual market values and sales data
- ✅ No production approval wait time
- ✅ Better structured data for card pricing
- ✅ Includes grading information, player data, and market trends

**How to Get API Key:**
1. Visit [Sports Card Pro API Documentation](https://www.sportscardspro.com/api-documentation)
2. Sign up for API access
3. Get your API key
4. Note rate limits and pricing tiers

### 1.5. Alternative: Get eBay API Keys (Legacy)

If you prefer to use eBay API instead:

1. Go to [eBay Developer Program](https://developer.ebay.com/)
2. Sign up or log in with your eBay account
3. Navigate to **"My Account" > "Application Keys"**
4. Click **"Create an Application Key"**
5. Fill out the application form:
   - Application Title: "Sports Card Bot" (or your choice)
   - Select: "I want to use eBay APIs"
6. Once approved, you'll receive:
   - **App ID (Client ID)** - This is your `EBAY_APP_ID`
   - **Cert ID (Client Secret)** - This is your `EBAY_CERT_ID`
   - **Dev ID** - This is your `EBAY_DEV_ID`

> **Note:** For basic functionality, you only need the **App ID**. The Cert ID and Dev ID are for advanced features.

### 1.6. API Comparison

**Sports Card Pro (Recommended):**
- ✅ Works immediately after getting API key
- ✅ Sports card-specific data and pricing
- ✅ Includes grading information (PSA, BGS, SGC, etc.)
- ✅ Market values based on actual sales data
- ✅ No production approval wait time
- ✅ Better player and set filtering

**eBay (Legacy):**
- 🧪 Sandbox: Test data, works immediately
- 🚀 Production: Real listings, requires approval (1-3 business days)
- ⚠️ Not sports card-specific
- ⚠️ Requires comparing sold vs active listings manually
- ✅ Can find active arbitrage opportunities

**Getting Started with eBay Sandbox:**

1. Go to https://developer.ebay.com/my/keys
2. Get your **Sandbox** keys (available immediately under "Sandbox Keys")
3. Add to `.env`: `EBAY_ENVIRONMENT=sandbox`
4. Test the bot with sandbox data

**Upgrading to Production:**

1. Request production access at https://developer.ebay.com/my/keys
2. Wait for eBay approval (1-3 business days)
3. Update `.env` with production keys
4. Change `EBAY_ENVIRONMENT=production`
5. Restart bot for real eBay data

### 2. Installation

```bash
# Clone the repository
git clone https://github.com/gopforever/sportscardbot.git
cd sportscardbot

# Install dependencies
pip install -r requirements.txt

# Configure API credentials
cp .env.example .env
```

### 3. Configuration

Edit the `.env` file with your API credentials:

**For Sports Card Pro (Recommended):**
```env
SPORTSCARDPRO_API_KEY=your_actual_api_key_here
```

**For eBay (Optional/Legacy):**
```env
EBAY_APP_ID=your_actual_app_id_here
EBAY_CERT_ID=your_cert_id_here
EBAY_DEV_ID=your_dev_id_here
EBAY_ENVIRONMENT=sandbox
```

⚠️ **Security Note:** Never commit your `.env` file to version control!

### 4. Customize Search (Optional)

Edit `config.yaml` to customize your search parameters:

**For Sports Card Pro:**
```yaml
search:
  sports:
    - "Baseball"
    - "Basketball"
  players:
    - "Michael Jordan"
    - "LeBron James"
  years:
    - 2023
    - "1986-87"
  sets:
    - "Topps"
    - "Fleer"

analysis:
  discount_threshold: 20  # minimum % below market
  min_sold_samples: 5  # minimum comps needed

filters:
  min_price: 10
  max_price: 10000
  grades: ["PSA 10", "BGS 9.5"]
  grading_companies: ["PSA", "BGS", "SGC"]
```

**For eBay:**
```yaml
search:
  keywords:
    - "Michael Jordan PSA 10"
    - "LeBron James rookie"
```

### 5. Run the Dashboard

```bash
streamlit run dashboard.py
```

The dashboard will open in your browser at `http://localhost:8501`

### 6. Select API Source

In the dashboard sidebar:
1. Choose **"Sports Card Pro"** (recommended) or **"eBay"** (legacy)
2. Configure your search filters based on the selected API
3. Click "Search for Deals" to find opportunities

## 📖 Usage Guide

### Using the Dashboard

1. **Select API Source** (Sidebar Top):
   - Choose **Sports Card Pro** (recommended) for accurate market values
   - Or choose **eBay** (legacy) for marketplace listings
   
2. **Configure Search** (Left Sidebar):

   **For Sports Card Pro:**
   - Select sport (Baseball, Basketball, Football, etc.)
   - Enter player name
   - Specify year and set
   - Choose grading company and grade
   - Set price range filters
   
   **For eBay:**
   - Enter search keywords (one per line)
   - Set discount threshold
   - Choose days of sold data to analyze
   - Set minimum sold samples
   - Configure price filters

3. **Search for Deals**:
   - Click the "🔍 Search for Deals" button
   - Wait for the bot to search and analyze (may take 30-60 seconds)

4. **Review Results**:
   - View summary metrics (total deals, avg discount, profit potential)
   - Explore analytics charts (discount distribution, profit potential)
   - Browse opportunities sorted by your preference
   - Click expanders to see detailed card information

5. **Filter Results**:
   - Sort by discount %, profit, or price
   - Filter by minimum discount
   - Search within card titles

6. **Export Data**:
   - Click "📥 Export to CSV" to download results

### Search Tips

**Sports Card Pro (Recommended):**
- Use specific filters for better results
- Combine player name with sport for precision
- Filter by grade for investment-quality cards: `"PSA 10"`, `"BGS 9.5"`
- Search by year and set: `"2023"` + `"Topps Chrome"`
- Leave some fields empty for broader searches

**eBay (Legacy):**
- Include player name: `"Michael Jordan"`
- Specify grading: `"PSA 10"`, `"BGS 9.5"`
- Include card set: `"2023 Topps Chrome"`
- Combine specifics: `"LeBron James Prizm Silver PSA 10"`

**Analysis Settings:**
- Higher discount threshold = fewer but better deals
- More sold days = more reliable data but less responsive to trends
- Higher min samples = more reliable but may miss opportunities

## ⚙️ Configuration Reference

### config.yaml Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `search.keywords` | eBay search terms (legacy) | See config.yaml |
| `search.sports` | Sports filter for Sports Card Pro | `["Baseball", "Basketball"]` |
| `search.players` | Player names | `["Michael Jordan"]` |
| `search.years` | Card years | `[2023, "1986-87"]` |
| `search.sets` | Card sets | `["Topps", "Fleer"]` |
| `search.categories` | eBay category IDs (legacy) | `["212"]` (Sports Cards) |
| `search.listing_type` | eBay listing type (legacy) | `all` |
| `analysis.discount_threshold` | Min % below market to flag | `20` |
| `analysis.sold_days` | Days of sold data (eBay) | `30` |
| `analysis.min_sold_samples` | Min sold comps needed | `5` |
| `analysis.recency_weight` | Weight for recent sales (0-1) | `0.7` |
| `filters.min_price` | Minimum price filter ($) | `10` |
| `filters.max_price` | Maximum price filter ($) | `10000` |
| `filters.grades` | Grade filters | `["PSA 10", "BGS 9.5"]` |
| `filters.grading_companies` | Grading company filters | `["PSA", "BGS", "SGC"]` |
| `filters.condition` | Condition filter (eBay) | `""` (all) |
| `api.max_results` | Max results per search | `100` |
| `api.cache_duration` | Cache duration (minutes) | `30` |
| `api.rate_limit` | API calls per minute | `60` |

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `SPORTSCARDPRO_API_KEY` | For Sports Card Pro | Sports Card Pro API Key |
| `EBAY_APP_ID` | For eBay | eBay Application ID (App ID) |
| `EBAY_CERT_ID` | No | eBay Certificate ID (for advanced features) |
| `EBAY_DEV_ID` | No | eBay Developer ID (for advanced features) |
| `EBAY_ENVIRONMENT` | No | API environment: `sandbox` or `production` (default: `sandbox`) |

## 📁 Project Structure

```
sportscardbot/
├── README.md                      # This file
├── requirements.txt               # Python dependencies
├── .env.example                  # API credentials template
├── .gitignore                    # Git ignore rules
├── config.yaml                   # Search configuration
├── dashboard.py                  # Streamlit dashboard (main entry)
├── src/
│   ├── __init__.py               # Package initialization
│   ├── sportscardpro_client.py  # Sports Card Pro API wrapper
│   ├── ebay_client.py            # eBay API wrapper (legacy)
│   ├── price_analyzer.py         # Price analysis engine
│   └── utils.py                  # Utility functions
```

## 🔧 Troubleshooting

### "Sports Card Pro API credentials not configured!"

**Solution:** Make sure you've:
1. Created a `.env` file (copy from `.env.example`)
2. Added your actual `SPORTSCARDPRO_API_KEY` from Sports Card Pro
3. Restarted the Streamlit app

### "Invalid API key" or 401 Errors

**Solution:**
- Verify your API key is correct in `.env`
- Check that there are no extra spaces or quotes
- Ensure your Sports Card Pro account is active
- Contact Sports Card Pro support if issues persist

### "Rate limit exceeded"

**Solution:**
- Sports Card Pro has rate limits (typically 60 requests/minute)
- Wait a few minutes before searching again
- Consider upgrading to a higher tier for more requests
- The bot automatically rate-limits to respect API limits

### "eBay API credentials not configured!" (Legacy)

**Solution:** Make sure you've:
1. Created a `.env` file (copy from `.env.example`)
2. Added your actual `EBAY_APP_ID` from eBay Developer portal
3. Restarted the Streamlit app

### "500 Internal Server Error" or Production API errors

**Solution:**
- Production API access requires eBay approval (1-3 business days)
- Switch to sandbox environment while waiting for approval:
  1. Set `EBAY_ENVIRONMENT=sandbox` in `.env`
  2. Use sandbox API keys from eBay Developer portal
  3. Restart the app
- Once production access is approved, switch back to `EBAY_ENVIRONMENT=production`

### "No opportunities found"

**Possible causes:**
- Discount threshold too high - try lowering it
- Search filters too specific - try broader terms
- Price filters too restrictive - widen the range
- Market conditions: cards may be fairly priced at the moment

**For Sports Card Pro:**
- Try searching with fewer filters
- Use more popular players or sets
- Adjust the price range

**For eBay:**
- Not enough sold listings - try increasing sold_days or decreasing min_sold_samples
- Use more generic search terms

### "Insufficient sold listings"

**Solution:**
- Lower `min_sold_samples` in sidebar or config.yaml
- Use more generic search terms
- Increase `sold_days` to look further back

### API Rate Limit Errors

**Sports Card Pro:**
- The bot automatically rate-limits to 60 calls/min
- Check your plan's limits on the Sports Card Pro dashboard
- Consider upgrading for higher limits

**eBay (Legacy):**
- The bot automatically rate-limits to 50 calls/min
- If you hit daily limits (5,000 calls), wait 24 hours
- Consider upgrading to eBay's paid tier for more calls

### Connection/Timeout Errors

**Solution:**
- Check your internet connection
- API may be temporarily down - try again later
- Increase timeout in `sportscardpro_client.py` or `ebay_client.py` if needed

## 🛡️ Security Best Practices

- ✅ Never commit `.env` file to version control
- ✅ Use environment variables for API keys
- ✅ Keep dependencies updated
- ✅ Don't share your API keys publicly
- ✅ Review `.gitignore` to ensure secrets are excluded

## 📊 Understanding the Metrics

### Market Value Calculation

**Sports Card Pro:**
- Uses Sports Card Pro's proprietary market value algorithm
- Based on actual sales data from multiple marketplaces
- Regularly updated for accuracy
- Includes grading and condition adjustments

**eBay (Legacy):**
The bot calculates market value using:
- **Average Price** - Mean of all sold listings
- **Median Price** - Middle value of sold listings
- **Weighted Average** - Recent sales weighted more heavily (used as market value)

### Discount Percentage
```
Discount % = ((Market Value - Active Price) / Market Value) × 100
```

### Profit Potential
```
Potential Profit = Market Value - Active Price
Profit Margin % = (Potential Profit / Active Price) × 100
```

## 🚀 Future Enhancements

Potential features for future versions:
- 📧 Email/SMS notifications for new deals
- 📈 Historical tracking of card values and opportunities
- 🤖 Machine learning for better value prediction
- 🌐 Additional marketplace integrations (TCGPlayer, COMC, etc.)
- 🔔 Real-time monitoring and alerts
- 📱 Mobile app
- 💾 Database storage for historical data
- 📊 Advanced analytics and trend analysis
- 🤝 Automated bidding (advanced - use with caution)

## 🤝 Contributing

Contributions are welcome! Feel free to:
- Report bugs
- Suggest features
- Submit pull requests

## 📝 License

This project is for educational purposes. Please comply with:
- Sports Card Pro API Terms of Service
- eBay API Terms of Service (if using eBay)
- eBay User Agreement
- Applicable laws and regulations

## ⚠️ Disclaimer

This tool is for research and educational purposes only. The authors are not responsible for:
- Any financial decisions made using this tool
- Accuracy of price analysis
- API rate limit violations
- Any violations of eBay's terms of service

Always do your own research before making purchasing decisions.

## 📞 Support

For issues, questions, or suggestions:
- Open an issue on GitHub
- Check the Troubleshooting section above
- Review eBay API documentation

## 🙏 Acknowledgments

- Sports Card Pro for providing excellent sports card data and API
- eBay Finding API for marketplace data access
- Streamlit for the dashboard framework
- The sports card collecting community

---

**Happy card hunting! 🏀⚾🏈**
