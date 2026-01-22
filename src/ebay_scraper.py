"""eBay Web Scraper for finding card listings"""

import re
import time
import logging
import requests
from typing import List, Dict, Optional
from bs4 import BeautifulSoup
from urllib.parse import quote_plus
from src.utils import retry_on_failure

logger = logging.getLogger(__name__)

class eBayScraper:
    """
    Web scraper for eBay card listings
    
    Note: This scraper is for personal use only. 
    Be respectful of eBay's servers with rate limiting.
    """
    
    BASE_URL = "https://www.ebay.com"
    # Regex pattern for extracting shipping costs
    SHIPPING_PRICE_PATTERN = re.compile(r'\$?([\d,]+\.?\d*)')
    # Keywords to exclude from searches (non-sports card items)
    EXCLUDED_KEYWORDS = ['funko', 'pop', 'magic', 'pokemon', 'yugioh', 'comic', 'game', 'jersey']
    
    def __init__(self, delay_between_requests: float = 2.0):
        """
        Initialize eBay scraper
        
        Args:
            delay_between_requests: Seconds to wait between requests (be respectful!)
        """
        self.delay = delay_between_requests
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        })
        self.last_request_time = 0
        
        logger.info(f"eBay scraper initialized (delay: {delay_between_requests}s)")
    
    def _rate_limit(self):
        """Enforce rate limiting between requests"""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.delay:
            time.sleep(self.delay - elapsed)
        self.last_request_time = time.time()
    
    @retry_on_failure(max_retries=2, delay=3.0)
    def search_listings(
        self,
        query: str,
        condition: str = "Used",
        buy_it_now_only: bool = True,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        limit: int = 50
    ) -> List[Dict]:
        """
        Search for active eBay listings
        
        Args:
            query: Search query (e.g., "Michael Jordan 1986 Fleer PSA 10")
            condition: Item condition filter
            buy_it_now_only: Only show Buy It Now listings
            min_price: Minimum price filter
            max_price: Maximum price filter
            limit: Max number of results
        
        Returns:
            List of listing dictionaries
        """
        logger.info(f"Scraping eBay for: {query}")
        
        # Be respectful - rate limit
        self._rate_limit()
        
        # Build search URL with sports cards category
        encoded_query = quote_plus(query)
        url = f"{self.BASE_URL}/sch/i.html?_nkw={encoded_query}"
        
        # Add category filters for sports cards
        url += "&_sacat=212"  # Sports Mem, Cards & Fan Shop
        url += "&LH_TitleDesc=1"  # Search title and description
        
        # Filter to sports trading cards specifically
        url += "&_in_kw=1"  # Search in keywords
        # Encode excluded keywords properly
        excluded = '+'.join(quote_plus(kw) for kw in self.EXCLUDED_KEYWORDS)
        url += f"&_ex_kw={excluded}"  # Exclude non-cards
        
        # Add filters
        if buy_it_now_only:
            url += "&LH_BIN=1"  # Buy It Now only
        
        if min_price:
            url += f"&_udlo={int(min_price)}"
        
        if max_price:
            url += f"&_udhi={int(max_price)}"
        
        # Sort by price ascending (find cheapest first)
        url += "&_sop=15"
        
        try:
            response = self.session.get(url, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            listings = []
            
            # Find listing items - eBay uses various class names, try multiple selectors
            items = soup.find_all('li', class_='s-item')
            
            for item in items[:limit]:
                try:
                    listing = self._parse_listing(item)
                    if listing:
                        listings.append(listing)
                except Exception as e:
                    logger.debug(f"Failed to parse listing: {str(e)}")
                    continue
            
            logger.info(f"Found {len(listings)} eBay listings")
            return listings
            
        except Exception as e:
            logger.error(f"Failed to scrape eBay: {str(e)}")
            return []
    
    def _parse_listing(self, item) -> Optional[Dict]:
        """
        Parse a single eBay listing from HTML
        
        Args:
            item: BeautifulSoup element for listing
        
        Returns:
            Listing dictionary or None
        """
        try:
            # Extract title
            title_elem = item.find('div', class_='s-item__title')
            if not title_elem:
                return None
            title = title_elem.get_text(strip=True)
            
            # Skip sponsored or placeholder results
            if 'Shop on eBay' in title or title == '':
                return None
            
            # Extract price
            price_elem = item.find('span', class_='s-item__price')
            if not price_elem:
                return None
            
            price_text = price_elem.get_text(strip=True)
            price = self._parse_price(price_text)
            
            if price is None or price == 0:
                return None
            
            # Extract URL
            link_elem = item.find('a', class_='s-item__link')
            url = link_elem.get('href') if link_elem else ''
            
            # Extract image
            img_elem = item.find('img', class_='s-item__image-img')
            image_url = img_elem.get('src') if img_elem else ''
            
            # Extract condition
            condition_elem = item.find('span', class_='SECONDARY_INFO')
            condition = condition_elem.get_text(strip=True) if condition_elem else 'Unknown'
            
            # Extract shipping cost
            shipping_elem = item.find('span', class_='s-item__shipping')
            shipping_text = shipping_elem.get_text(strip=True) if shipping_elem else 'Unknown'
            shipping_cost = self._parse_shipping(shipping_text)
            
            return {
                'title': title,
                'price': price,
                'shipping_cost': shipping_cost,
                'total_cost': price + shipping_cost,
                'url': url,
                'image_url': image_url,
                'condition': condition,
                'marketplace': 'eBay',
                'source': 'scraper'
            }
            
        except Exception as e:
            logger.debug(f"Error parsing listing: {str(e)}")
            return None
    
    def _parse_price(self, price_text: str) -> Optional[float]:
        """
        Parse price from text like '$1,234.56' or '$100 to $200'
        
        Args:
            price_text: Raw price string
        
        Returns:
            Price as float or None
        """
        try:
            # Remove currency symbols and commas
            price_text = price_text.replace('$', '').replace(',', '').strip()
            
            # Handle price ranges (take the lower value)
            if ' to ' in price_text:
                price_text = price_text.split(' to ')[0].strip()
            
            return float(price_text)
        except (ValueError, AttributeError):
            return None
    
    def _parse_shipping(self, shipping_text: str) -> float:
        """
        Parse shipping cost from text
        
        Args:
            shipping_text: Raw shipping string
        
        Returns:
            Shipping cost as float (0 if free)
        """
        if not shipping_text:
            return 0.0
        
        shipping_lower = shipping_text.lower()
        
        if 'free' in shipping_lower:
            return 0.0
        
        try:
            # Extract number from text like '+$5.00 shipping'
            match = self.SHIPPING_PRICE_PATTERN.search(shipping_text)
            if match:
                return float(match.group(1).replace(',', ''))
        except (ValueError, AttributeError, IndexError) as e:
            logger.debug(f"Failed to parse shipping cost from '{shipping_text}': {e}")
        
        return 0.0
