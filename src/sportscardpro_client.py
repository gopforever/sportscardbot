"""Sports Card Pro API Client for sports card data and pricing"""

import os
import re
import time
import logging
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
import requests
from src.utils import retry_on_failure

logger = logging.getLogger(__name__)


class SportsCardProClient:
    """
    Wrapper for Sports Card Pro API (via PriceCharting.com)
    
    Documentation: https://www.pricecharting.com/api-documentation
    """
    
    BASE_URL = "https://www.pricecharting.com/api"
    
    def __init__(self, api_key: str, rate_limit_per_min: int = 60):
        """
        Initialize Sports Card Pro client
        
        Args:
            api_key: PriceCharting.com API key (from Sports Card Pro)
            rate_limit_per_min: Maximum API calls per minute
        """
        if not api_key or api_key == "your_api_key_here":
            raise ValueError("Valid Sports Card Pro API key is required. Please set SPORTSCARDPRO_API_KEY in .env file")
        
        self.api_key = api_key
        self.rate_limit_per_min = rate_limit_per_min
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'SportsCardBot/1.0'
        })
        
        logger.info("Sports Card Pro client initialized")
    
    @retry_on_failure(max_retries=3, delay=1.0)
    def _make_request(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict:
        """
        Make API request to PriceCharting API
        
        Args:
            endpoint: API endpoint ('product' or 'products')
            params: Query parameters (must include 't' for auth)
        
        Returns:
            Parsed JSON response
        """
        if params is None:
            params = {}
        
        # API requires 't' parameter - ensure it's present
        if 't' not in params:
            params['t'] = self.api_key
        
        url = f"{self.BASE_URL}/{endpoint}"
        
        try:
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            return data
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401 or e.response.status_code == 403:
                error_msg = "Invalid API key. Please check SPORTSCARDPRO_API_KEY in .env"
                logger.error(error_msg)
                raise Exception(error_msg) from e
            elif e.response.status_code == 429:
                error_msg = "Rate limit exceeded. Please try again later."
                logger.error(error_msg)
                raise Exception(error_msg) from e
            logger.error(f"Request failed: {str(e)}")
            raise
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {str(e)}")
            raise
    
    def search_cards(self, query: str, limit: int = 20) -> List[Dict]:
        """
        Search for sports cards using simple text query
        
        Args:
            query: Search query (e.g., "michael jordan 1986 fleer", "tom brady rookie")
            limit: Max results (API returns max 20, we can't control this)
        
        Returns:
            List of card dictionaries
        """
        logger.info(f"Searching cards with query: {query}")
        
        if not query:
            logger.warning("Empty search query provided")
            return []
        
        params = {
            't': self.api_key,
            'q': query
        }
        
        try:
            response = self._make_request('products', params)
            
            if response.get('status') != 'success':
                logger.error(f"API returned error: {response.get('error-message', 'Unknown error')}")
                return []
            
            # Parse results
            cards = []
            products = response.get('products', [])
            
            for product in products[:limit]:  # Limit results client-side
                try:
                    card = self._parse_card(product)
                    cards.append(card)
                except Exception as e:
                    logger.warning(f"Failed to parse card: {str(e)}")
                    continue
            
            logger.info(f"Found {len(cards)} cards")
            return cards
            
        except Exception as e:
            logger.error(f"Failed to search cards: {str(e)}")
            return []
    
    def get_card_details(self, card_id: str) -> Optional[Dict]:
        """
        Get detailed information for a specific card by ID
        
        Args:
            card_id: SportsCardsPro product ID
        
        Returns:
            Card details dictionary or None
        """
        logger.info(f"Getting details for card: {card_id}")
        
        params = {
            't': self.api_key,
            'id': card_id
        }
        
        try:
            response = self._make_request('product', params)
            
            if response.get('status') == 'success':
                return self._parse_card(response)
            else:
                logger.error(f"API error: {response.get('error-message')}")
                return None
                
        except Exception as e:
            logger.error(f"Failed to get card details: {str(e)}")
            return None
    
    def get_sales_history(self, card_id: str, days_back: int = 90, limit: int = 100) -> List[Dict]:
        """Sales history not supported by PriceCharting API"""
        logger.warning("Sales history not supported by PriceCharting API")
        return []
    
    def get_market_value(self, card_id: str) -> Optional[Dict]:
        """
        Get market value from product prices
        Uses the product API and extracts price data
        """
        product = self.get_card_details(card_id)
        if not product:
            return None
        
        return {
            'market_value': product.get('market_value', 0),
            'ungraded': product.get('price', 0),
            'psa_10': product.get('psa_10_price', 0),
            'graded_9': product.get('graded_9_price', 0),
        }
    
    def _parse_card(self, item: Dict) -> Dict:
        """
        Parse PriceCharting API product response
        
        Args:
            item: Raw product data from API
        
        Returns:
            Parsed card dictionary
        """
        def pennies_to_dollars(pennies):
            """Convert price in pennies to dollars"""
            if pennies is None:
                return 0.0
            try:
                return float(pennies) / 100.0
            except (ValueError, TypeError):
                return 0.0
        
        # Extract set and card name from console-name and product-name
        set_name = item.get('console-name', '')
        card_name = item.get('product-name', '')
        
        # Parse prices (all in pennies, convert to dollars)
        # According to PriceCharting API docs:
        # - loose-price: Ungraded card value
        # - graded-price: Graded 9 value
        # - manual-only-price: PSA 10 value
        # - new-price: Graded 8/8.5 value
        # - cib-price: Graded 7/7.5 value
        # - bgs-10-price: BGS 10 value
        loose_price = pennies_to_dollars(item.get('loose-price'))
        graded_9_price = pennies_to_dollars(item.get('graded-price'))
        psa_10_price = pennies_to_dollars(item.get('manual-only-price'))
        graded_8_price = pennies_to_dollars(item.get('new-price'))
        graded_7_price = pennies_to_dollars(item.get('cib-price'))
        bgs_10_price = pennies_to_dollars(item.get('bgs-10-price'))
        
        # Use highest available price as market value
        # Rationale: For investment analysis, the highest graded value represents
        # the maximum market potential of the card. Users can access individual
        # grade prices if they need more specific valuations.
        market_value = max(psa_10_price, bgs_10_price, graded_9_price, graded_8_price, loose_price)
        
        return {
            'card_id': item.get('id', ''),
            'title': f"{card_name} - {set_name}",
            'player': card_name,  # Product name contains player info
            'set': set_name,
            'sport': self._extract_sport(set_name),
            'year': self._extract_year(set_name),
            'card_number': '',  # Not separately provided
            'grade': '',
            'grading_company': '',
            'price': loose_price,  # Ungraded price
            'market_value': market_value,
            'psa_10_price': psa_10_price,
            'graded_9_price': graded_9_price,
            'graded_8_price': graded_8_price,
            'graded_7_price': graded_7_price,
            'bgs_10_price': bgs_10_price,
            'image_url': '',  # Not provided by API
            'description': f"{card_name} from {set_name}",
            'genre': item.get('genre', ''),
            'release_date': item.get('release-date', ''),
        }
    
    def _extract_sport(self, set_name: str) -> str:
        """Extract sport from set name"""
        set_lower = set_name.lower()
        if 'basketball' in set_lower:
            return 'Basketball'
        elif 'baseball' in set_lower:
            return 'Baseball'
        elif 'football' in set_lower:
            return 'Football'
        elif 'hockey' in set_lower:
            return 'Hockey'
        elif 'soccer' in set_lower:
            return 'Soccer'
        return ''
    
    def _extract_year(self, set_name: str) -> str:
        """Extract year from set name (e.g., '1986 Fleer' -> '1986')"""
        match = re.search(r'\b(19|20)\d{2}\b', set_name)
        return match.group(0) if match else ''

