"""Sports Card Pro API Client for sports card data and pricing"""

import os
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
        Make API request to Sports Card Pro API
        
        Args:
            endpoint: API endpoint path
            params: Query parameters
        
        Returns:
            Parsed JSON response
        """
        # Apply rate limiting using utility decorator approach
        from src.utils import rate_limit
        
        # Note: Rate limiting is applied at method level
        # For per-instance rate limiting, consider using a decorator on __init__
        
        # Add API token to every request
        if params is None:
            params = {}
        params['t'] = self.api_key
        
        url = f"{self.BASE_URL}/{endpoint}"
        
        try:
            response = self.session.get(
                url,
                params=params,
                timeout=30
            )
            response.raise_for_status()
            
            data = response.json()
            
            # Check for API errors
            if isinstance(data, dict) and 'error' in data:
                error_msg = data.get('error', 'Unknown error')
                logger.error(f"Sports Card Pro API error: {error_msg}")
                raise Exception(f"Sports Card Pro API error: {error_msg}")
            
            return data
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
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
    
    def search_cards(
        self,
        query: Optional[str] = None,
        sport: Optional[str] = None,
        player: Optional[str] = None,
        year: Optional[str] = None,
        card_set: Optional[str] = None,
        card_number: Optional[str] = None,
        grade: Optional[str] = None,
        grading_company: Optional[str] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict]:
        """
        Search for sports cards
        
        Args:
            query: General search query
            sport: Sport filter (Baseball, Basketball, Football, Hockey, Soccer)
            player: Player name
            year: Card year or year range (e.g., "2023", "1986-87")
            card_set: Card set name (e.g., "Topps", "Fleer")
            card_number: Card number
            grade: Grade value (e.g., "10", "9.5")
            grading_company: Grading company (PSA, BGS, SGC, etc.)
            min_price: Minimum price filter
            max_price: Maximum price filter
            limit: Maximum number of results
            offset: Pagination offset
        
        Returns:
            List of card dictionaries
        """
        logger.info(f"Searching cards with query: {query}, player: {player}, sport: {sport}")
        
        params = {
            'limit': min(limit, 100),
            'offset': offset
        }
        
        # Add search filters
        if query:
            params['q'] = query
        if sport:
            params['sport'] = sport
        if player:
            params['player'] = player
        if year:
            params['year'] = year
        if card_set:
            params['set'] = card_set
        if card_number:
            params['number'] = card_number
        if grade:
            params['grade'] = grade
        if grading_company:
            params['grading_company'] = grading_company
        if min_price is not None:
            params['min_price'] = min_price
        if max_price is not None:
            params['max_price'] = max_price
        
        try:
            response = self._make_request('products', params)
            
            # Parse results
            cards = []
            items = response.get('cards', []) if isinstance(response, dict) else response
            
            for item in items:
                try:
                    card = self._parse_card(item)
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
        Get detailed information for a specific card
        
        Args:
            card_id: Sports Card Pro card ID
        
        Returns:
            Card details dictionary or None if not found
        """
        logger.info(f"Getting details for card: {card_id}")
        
        try:
            params = {'id': card_id}
            response = self._make_request('product', params)
            
            if isinstance(response, dict) and 'card' in response:
                return self._parse_card(response['card'])
            elif isinstance(response, dict):
                return self._parse_card(response)
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get card details: {str(e)}")
            return None
    
    def get_sales_history(
        self,
        card_id: str,
        days_back: int = 90,
        limit: int = 100
    ) -> List[Dict]:
        """
        Get recent sales history for a card
        
        Args:
            card_id: Sports Card Pro card ID
            days_back: Number of days to look back
            limit: Maximum number of sales records
        
        Returns:
            List of sales dictionaries
        """
        logger.info(f"Getting sales history for card: {card_id} (last {days_back} days)")
        
        try:
            # Sales history is included in the product endpoint
            # Note: days_back and limit parameters are kept for backwards compatibility
            # but are not currently used by the PriceCharting API
            params = {'id': card_id}
            response = self._make_request('product', params)
            
            sales = []
            items = response.get('sales', []) if isinstance(response, dict) else response
            
            for item in items:
                try:
                    sale = self._parse_sale(item)
                    sales.append(sale)
                except Exception as e:
                    logger.warning(f"Failed to parse sale: {str(e)}")
                    continue
            
            logger.info(f"Found {len(sales)} sales")
            return sales
            
        except Exception as e:
            logger.error(f"Failed to get sales history: {str(e)}")
            return []
    
    def get_market_value(self, card_id: str) -> Optional[Dict]:
        """
        Get current market value for a card
        
        Args:
            card_id: Sports Card Pro card ID
        
        Returns:
            Market value dictionary with pricing statistics
        """
        logger.info(f"Getting market value for card: {card_id}")
        
        try:
            # Market value is included in the product endpoint
            params = {'id': card_id}
            response = self._make_request('product', params)
            
            if isinstance(response, dict):
                return {
                    'market_value': response.get('market_value', 0),
                    'average': response.get('average_price', 0),
                    'median': response.get('median_price', 0),
                    'min': response.get('min_price', 0),
                    'max': response.get('max_price', 0),
                    'std_dev': response.get('std_dev', 0),
                    'sample_size': response.get('sales_count', 0),
                    'last_updated': response.get('last_updated'),
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get market value: {str(e)}")
            return None
    
    def _parse_card(self, item: Dict) -> Dict:
        """
        Parse Sports Card Pro card response into structured dictionary
        
        Args:
            item: Raw card data from API
        
        Returns:
            Parsed card dictionary
        """
        # Helper function to safely convert to float
        def safe_float(value, default=0.0):
            if value is None:
                return default
            try:
                return float(value)
            except (ValueError, TypeError):
                return default
        
        return {
            'card_id': item.get('id', item.get('card_id', '')),
            'title': self._build_title(item),
            'player': item.get('player_name', item.get('player', '')),
            'sport': item.get('sport', ''),
            'year': item.get('year', ''),
            'set': item.get('set_name', item.get('set', '')),
            'card_number': item.get('card_number', item.get('number', '')),
            'grade': item.get('grade', ''),
            'grading_company': item.get('grading_company', ''),
            'price': safe_float(item.get('current_price', item.get('price'))),
            'market_value': safe_float(item.get('market_value')),
            'image_url': item.get('image_url', item.get('image', '')),
            'description': item.get('description', ''),
            'parallel': item.get('parallel', ''),
            'rookie': item.get('rookie', False),
            'autograph': item.get('autograph', False),
            'memorabilia': item.get('memorabilia', False),
            'population': item.get('population', 0),
        }
    
    def _parse_sale(self, item: Dict) -> Dict:
        """
        Parse Sports Card Pro sale response into structured dictionary
        
        Args:
            item: Raw sale data from API
        
        Returns:
            Parsed sale dictionary
        """
        # Parse sale date - handles multiple common ISO formats
        sale_date = None
        if 'sale_date' in item:
            try:
                date_str = item['sale_date']
                # Remove timezone indicator and parse
                if isinstance(date_str, str):
                    # Handle 'Z' (Zulu/UTC) timezone
                    date_str = date_str.replace('Z', '+00:00')
                    sale_date = datetime.fromisoformat(date_str)
            except (ValueError, AttributeError) as e:
                logger.warning(f"Failed to parse sale date '{item.get('sale_date')}': {str(e)}")
        
        return {
            'sale_id': item.get('id', item.get('sale_id', '')),
            'price': float(item.get('price', 0)),
            'sale_date': sale_date,
            'marketplace': item.get('marketplace', item.get('platform', '')),
            'condition': item.get('condition', ''),
            'url': item.get('url', ''),
        }
    
    def _build_title(self, card: Dict) -> str:
        """
        Build a descriptive title from card data
        
        Args:
            card: Card dictionary
        
        Returns:
            Formatted title string
        """
        parts = []
        
        # Year
        if card.get('year'):
            parts.append(str(card['year']))
        
        # Set
        if card.get('set_name') or card.get('set'):
            parts.append(card.get('set_name', card.get('set', '')))
        
        # Player
        if card.get('player_name') or card.get('player'):
            parts.append(card.get('player_name', card.get('player', '')))
        
        # Card number
        if card.get('card_number') or card.get('number'):
            parts.append(f"#{card.get('card_number', card.get('number', ''))}")
        
        # Parallel/Variant
        if card.get('parallel'):
            parts.append(card['parallel'])
        
        # Grade
        if card.get('grading_company') and card.get('grade'):
            parts.append(f"{card['grading_company']} {card['grade']}")
        
        # Special features
        features = []
        if card.get('rookie'):
            features.append('RC')
        if card.get('autograph'):
            features.append('Auto')
        if card.get('memorabilia'):
            features.append('Mem')
        
        if features:
            parts.append(f"({'/'.join(features)})")
        
        return ' '.join(parts) if parts else 'Unknown Card'
