# 🏀 Sports Card Bot

A Python-based bot that searches eBay for sports cards selling below market value by comparing active listings against recent sold listings, with an interactive price comparison dashboard.

## 🎯 Overview

Sports Card Bot helps collectors and traders discover underpriced sports cards on eBay by:
- **Searching** active eBay listings for sports cards
- **Analyzing** recent sold listings to calculate market value
- **Identifying** cards listed below market value (potential deals)
- **Displaying** opportunities in an interactive dashboard with detailed analytics

## ✨ Features

### Core Functionality
- 🔍 **eBay API Integration** - Uses official eBay Finding API (free tier, 5,000 calls/day)
- 📊 **Price Analysis** - Calculates market value from sold listings (average, median, weighted by recency)
- 🎯 **Deal Detection** - Identifies underpriced cards below your threshold (default 20%)
- 💰 **Profit Calculator** - Shows potential profit and margins for each opportunity
- 📈 **Interactive Dashboard** - Streamlit-based web interface with charts and filters

### Dashboard Features
- Table view of opportunities sorted by discount percentage
- Card image thumbnails
- Price comparison metrics (active price vs. market value)
- Filter and search within results
- Export results to CSV
- Real-time analytics charts
- Customizable search parameters

## 🚀 Quick Start

### Prerequisites
- Python 3.8 or higher
- eBay Developer account (free)

### 1. Get eBay API Keys

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

### 1.5. Sandbox vs Production

eBay provides two environments for testing and production use:

**🧪 Sandbox Environment:**
- For testing and development
- Works immediately after getting API keys
- Uses test/simulated data (not real eBay listings)
- No approval process required
- Perfect for testing the bot's functionality

**🚀 Production Environment:**
- Real eBay data and listings
- Requires eBay approval (typically 1-3 business days)
- Use for actual card price analysis
- Switch after testing is complete

**Getting Started with Sandbox:**

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

Edit the `.env` file with your eBay API credentials:

```env
EBAY_APP_ID=your_actual_app_id_here
EBAY_CERT_ID=your_cert_id_here
EBAY_DEV_ID=your_dev_id_here
EBAY_ENVIRONMENT=sandbox
```

⚠️ **Security Note:** Never commit your `.env` file to version control!

### 4. Customize Search (Optional)

Edit `config.yaml` to customize your search parameters:

```yaml
search:
  keywords:
    - "Michael Jordan PSA 10"
    - "LeBron James rookie"
    - "Tom Brady rookie PSA"
  
analysis:
  discount_threshold: 20  # minimum % below market
  sold_days: 30  # days of sold data
  min_sold_samples: 5  # minimum comps needed

filters:
  min_price: 10
  max_price: 1000
```

### 5. Run the Dashboard

```bash
streamlit run dashboard.py
```

The dashboard will open in your browser at `http://localhost:8501`

## 📖 Usage Guide

### Using the Dashboard

1. **Configure Search** (Left Sidebar):
   - Enter search keywords (one per line)
   - Set discount threshold (minimum discount to flag)
   - Choose days of sold data to analyze
   - Set minimum sold samples for reliable data
   - Configure price filters

2. **Search for Deals**:
   - Click the "🔍 Search for Deals" button
   - Wait for the bot to search and analyze (may take 30-60 seconds)

3. **Review Results**:
   - View summary metrics (total deals, avg discount, profit potential)
   - Explore analytics charts (discount distribution, profit potential)
   - Browse opportunities sorted by your preference
   - Click expanders to see detailed card information

4. **Filter Results**:
   - Sort by discount %, profit, or price
   - Filter by minimum discount
   - Search within card titles

5. **Export Data**:
   - Click "📥 Export to CSV" to download results

### Search Tips

**Effective Keywords:**
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
| `search.keywords` | List of search terms | See config.yaml |
| `search.categories` | eBay category IDs | `["212"]` (Sports Cards) |
| `search.listing_type` | Filter by type: all/auction/fixed | `all` |
| `analysis.discount_threshold` | Min % below market to flag | `20` |
| `analysis.sold_days` | Days of sold data | `30` |
| `analysis.min_sold_samples` | Min sold comps needed | `5` |
| `analysis.recency_weight` | Weight for recent sales (0-1) | `0.7` |
| `filters.min_price` | Minimum price filter ($) | `10` |
| `filters.max_price` | Maximum price filter ($) | `1000` |
| `filters.condition` | Condition filter | `""` (all) |
| `api.max_results` | Max results per search | `100` |
| `api.cache_duration` | Cache duration (minutes) | `30` |
| `api.rate_limit` | API calls per minute | `50` |

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `EBAY_APP_ID` | Yes | eBay Application ID (App ID) |
| `EBAY_CERT_ID` | No | eBay Certificate ID (for advanced features) |
| `EBAY_DEV_ID` | No | eBay Developer ID (for advanced features) |
| `EBAY_ENVIRONMENT` | No | API environment: `sandbox` or `production` (default: `sandbox`) |

## 📁 Project Structure

```
sportscardbot/
├── README.md                 # This file
├── requirements.txt          # Python dependencies
├── .env.example             # API credentials template
├── .gitignore               # Git ignore rules
├── config.yaml              # Search configuration
├── dashboard.py             # Streamlit dashboard (main entry)
├── src/
│   ├── __init__.py          # Package initialization
│   ├── ebay_client.py       # eBay API wrapper
│   ├── price_analyzer.py    # Price analysis engine
│   └── utils.py             # Utility functions
```

## 🔧 Troubleshooting

### "eBay API credentials not configured!"

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
- Search keywords too specific - try broader terms
- Price filters too restrictive - widen the range
- Not enough sold listings - try increasing sold_days or decreasing min_sold_samples

### "Insufficient sold listings"

**Solution:**
- Lower `min_sold_samples` in sidebar or config.yaml
- Use more generic search terms
- Increase `sold_days` to look further back

### API Rate Limit Errors

**Solution:**
- The bot automatically rate-limits to 50 calls/min
- If you hit daily limits (5,000 calls), wait 24 hours
- Consider upgrading to eBay's paid tier for more calls

### Connection/Timeout Errors

**Solution:**
- Check your internet connection
- eBay API may be temporarily down - try again later
- Increase timeout in `ebay_client.py` if needed

## 🛡️ Security Best Practices

- ✅ Never commit `.env` file to version control
- ✅ Use environment variables for API keys
- ✅ Keep dependencies updated
- ✅ Don't share your API keys publicly
- ✅ Review `.gitignore` to ensure secrets are excluded

## 📊 Understanding the Metrics

### Market Value Calculation
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
- 📈 Historical tracking of opportunities
- 🤖 Machine learning for better value prediction
- 🌐 Multi-marketplace support (TCGPlayer, COMC, etc.)
- 🔔 Real-time monitoring and alerts
- 📱 Mobile app
- 🤝 Automated bidding (advanced)

## 🤝 Contributing

Contributions are welcome! Feel free to:
- Report bugs
- Suggest features
- Submit pull requests

## 📝 License

This project is for educational purposes. Please comply with:
- eBay API Terms of Service
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

- eBay Finding API for data access
- Streamlit for the dashboard framework
- The sports card collecting community

---

**Happy card hunting! 🏀⚾🏈**
