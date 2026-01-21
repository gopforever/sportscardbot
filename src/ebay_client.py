"""eBay API Client for finding and analyzing sports card listings"""

import os
import time
import logging
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
import requests
from urllib.parse import urlencode
from src.utils import retry_on_failure

logger = logging.getLogger(__name__)


class eBayClient:
    """
    Wrapper for eBay Finding API
    
    Documentation: https://developer.ebay.com/devzone/finding/Concepts/FindingAPIGuide.html
    """
    
    PRODUCTION_URL = "https://svcs.ebay.com/services/search/FindingService/v1"
    SANDBOX_URL = "https://svcs.sandbox.ebay.com/services/search/FindingService/v1"
    
    def __init__(self, app_id: str, environment: str = 'sandbox', rate_limit_per_min: int = 50):
        """
        Initialize eBay client
        
        Args:
            app_id: eBay Application ID (API key)
            environment: API environment ('sandbox' or 'production')
            rate_limit_per_min: Maximum API calls per minute
        """
        if not app_id or app_id == "your_app_id_here":
            raise ValueError("Valid eBay APP ID is required. Please set EBAY_APP_ID in .env file")
        
        self.app_id = app_id
        self.environment = environment.lower()
        self.rate_limit_per_min = rate_limit_per_min
        
        # Set base URL based on environment
        if self.environment == 'sandbox':
            self.base_url = self.SANDBOX_URL
        else:
            self.base_url = self.PRODUCTION_URL
        
        logger.info(f"eBay client initialized ({self.environment} environment)")
    
    @retry_on_failure(max_retries=3, delay=1.0)
    def _make_request(self, operation: str, params: Dict[str, Any]) -> Dict:
        """
        Make API request to eBay Finding API
        
        Args:
            operation: API operation name
            params: Request parameters
        
        Returns:
            Parsed JSON response
        """
        # Apply rate limiting
        time.sleep(60.0 / self.rate_limit_per_min)
        
        # Build request parameters
        request_params = {
            'OPERATION-NAME': operation,
            'SERVICE-VERSION': '1.0.0',
            'SECURITY-APPNAME': self.app_id,
            'RESPONSE-DATA-FORMAT': 'JSON',
            'REST-PAYLOAD': '',
        }
        request_params.update(params)
        
        try:
            response = requests.get(
                self.base_url,
                params=request_params,
                timeout=30
            )
            response.raise_for_status()
            
            data = response.json()
            
            # Check for API errors
            if 'errorMessage' in data:
                error_msg = data['errorMessage'][0]['error'][0]['message'][0]
                logger.error(f"eBay API error: {error_msg}")
                raise Exception(f"eBay API error: {error_msg}")
            
            return data
            
        except requests.exceptions.HTTPError as e:
            # Handle 500 errors with helpful message
            if e.response.status_code == 500 and self.environment == 'production':
                error_msg = (
                    "Production API access may not be approved yet. "
                    "Try using sandbox environment by setting EBAY_ENVIRONMENT=sandbox in .env"
                )
                logger.error(error_msg)
                raise Exception(error_msg) from e
            logger.error(f"Request failed: {str(e)}")
            raise
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {str(e)}")
            raise
    
    def search_active_listings(
        self,
        keywords: str,
        category_id: Optional[str] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        condition: Optional[str] = None,
        listing_type: str = "all",
        max_results: int = 100
    ) -> List[Dict]:
        """
        Search for active eBay listings
        
        Args:
            keywords: Search keywords
            category_id: eBay category ID
            min_price: Minimum price filter
            max_price: Maximum price filter
            condition: Item condition filter
            listing_type: Type of listing (all, auction, fixed)
            max_results: Maximum number of results
        
        Returns:
            List of listing dictionaries
        """
        logger.info(f"Searching active listings for: {keywords}")
        
        params = {
            'keywords': keywords,
            'paginationInput.entriesPerPage': min(max_results, 100),
        }
        
        # Add filters
        filter_index = 0
        
        if category_id:
            params[f'categoryId'] = category_id
        
        if min_price is not None:
            params[f'itemFilter({filter_index}).name'] = 'MinPrice'
            params[f'itemFilter({filter_index}).value'] = str(min_price)
            filter_index += 1
        
        if max_price is not None:
            params[f'itemFilter({filter_index}).name'] = 'MaxPrice'
            params[f'itemFilter({filter_index}).value'] = str(max_price)
            filter_index += 1
        
        if condition:
            condition_map = {
                'New': '1000',
                'Used': '3000',
                'Not Specified': '0'
            }
            if condition in condition_map:
                params[f'itemFilter({filter_index}).name'] = 'Condition'
                params[f'itemFilter({filter_index}).value'] = condition_map[condition]
                filter_index += 1
        
        if listing_type != "all":
            type_map = {
                'auction': 'Auction',
                'fixed': 'FixedPrice'
            }
            if listing_type in type_map:
                params[f'itemFilter({filter_index}).name'] = 'ListingType'
                params[f'itemFilter({filter_index}).value'] = type_map[listing_type]
                filter_index += 1
        
        # Make request
        try:
            response = self._make_request('findItemsAdvanced', params)
            
            # Parse results
            listings = []
            search_result = response.get('findItemsAdvancedResponse', [{}])[0]
            
            if 'searchResult' not in search_result:
                logger.warning("No search results found")
                return listings
            
            items = search_result['searchResult'][0].get('item', [])
            
            for item in items:
                try:
                    listing = self._parse_listing(item)
                    listings.append(listing)
                except Exception as e:
                    logger.warning(f"Failed to parse listing: {str(e)}")
                    continue
            
            logger.info(f"Found {len(listings)} active listings")
            return listings
            
        except Exception as e:
            logger.error(f"Failed to search active listings: {str(e)}")
            return []
    
    def search_sold_listings(
        self,
        keywords: str,
        category_id: Optional[str] = None,
        days_back: int = 30,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        max_results: int = 100
    ) -> List[Dict]:
        """
        Search for completed/sold eBay listings
        
        Args:
            keywords: Search keywords
            category_id: eBay category ID
            days_back: Number of days to look back
            min_price: Minimum price filter
            max_price: Maximum price filter
            max_results: Maximum number of results
        
        Returns:
            List of sold listing dictionaries
        """
        logger.info(f"Searching sold listings for: {keywords} (last {days_back} days)")
        
        params = {
            'keywords': keywords,
            'paginationInput.entriesPerPage': min(max_results, 100),
        }
        
        # Add filters
        filter_index = 0
        
        if category_id:
            params['categoryId'] = category_id
        
        # Filter for sold items
        params[f'itemFilter({filter_index}).name'] = 'SoldItemsOnly'
        params[f'itemFilter({filter_index}).value'] = 'true'
        filter_index += 1
        
        if min_price is not None:
            params[f'itemFilter({filter_index}).name'] = 'MinPrice'
            params[f'itemFilter({filter_index}).value'] = str(min_price)
            filter_index += 1
        
        if max_price is not None:
            params[f'itemFilter({filter_index}).name'] = 'MaxPrice'
            params[f'itemFilter({filter_index}).value'] = str(max_price)
            filter_index += 1
        
        # Make request
        try:
            response = self._make_request('findCompletedItems', params)
            
            # Parse results
            sold_listings = []
            search_result = response.get('findCompletedItemsResponse', [{}])[0]
            
            if 'searchResult' not in search_result:
                logger.warning("No sold listings found")
                return sold_listings
            
            items = search_result['searchResult'][0].get('item', [])
            
            cutoff_date = datetime.now() - timedelta(days=days_back)
            
            for item in items:
                try:
                    listing = self._parse_listing(item, is_sold=True)
                    
                    # Filter by date
                    if listing.get('end_time'):
                        if listing['end_time'] >= cutoff_date:
                            sold_listings.append(listing)
                    else:
                        sold_listings.append(listing)
                        
                except Exception as e:
                    logger.warning(f"Failed to parse sold listing: {str(e)}")
                    continue
            
            logger.info(f"Found {len(sold_listings)} sold listings")
            return sold_listings
            
        except Exception as e:
            logger.error(f"Failed to search sold listings: {str(e)}")
            return []
    
    def _parse_listing(self, item: Dict, is_sold: bool = False) -> Dict:
        """
        Parse eBay API item response into structured dictionary
        
        Args:
            item: Raw item data from API
            is_sold: Whether this is a sold listing
        
        Returns:
            Parsed listing dictionary
        """
        # Extract basic info
        item_id = item.get('itemId', [''])[0]
        title = item.get('title', [''])[0]
        
        # Extract price
        price_info = item.get('sellingStatus', [{}])[0]
        price_data = price_info.get('currentPrice' if not is_sold else 'convertedCurrentPrice', [{}])[0]
        price = float(price_data.get('__value__', 0))
        currency = price_data.get('@currencyId', 'USD')
        
        # Extract condition
        condition_info = item.get('condition', [{}])[0]
        condition = condition_info.get('conditionDisplayName', ['Not Specified'])[0]
        
        # Extract URL and image
        url = item.get('viewItemURL', [''])[0]
        image_url = item.get('galleryURL', [''])[0]
        
        # Extract seller info
        seller_info = item.get('sellerInfo', [{}])[0]
        seller_name = seller_info.get('sellerUserName', [''])[0]
        
        # Extract listing type
        listing_info = item.get('listingInfo', [{}])[0]
        listing_type = listing_info.get('listingType', [''])[0]
        
        # Extract end time for sold listings
        end_time = None
        if is_sold and 'endTime' in listing_info:
            try:
                end_time_str = listing_info['endTime'][0]
                end_time = datetime.fromisoformat(end_time_str.replace('Z', '+00:00'))
            except Exception as e:
                logger.warning(f"Failed to parse end time: {str(e)}")
        
        return {
            'item_id': item_id,
            'title': title,
            'price': price,
            'currency': currency,
            'condition': condition,
            'url': url,
            'image_url': image_url,
            'seller_name': seller_name,
            'listing_type': listing_type,
            'end_time': end_time,
            'is_sold': is_sold,
        }
