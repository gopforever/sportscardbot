"""Price analysis engine for comparing active listings vs market value"""

import logging
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class PriceAnalyzer:
    """
    Analyzes sports card prices to identify underpriced opportunities
    """
    
    # Maximum price multiplier for scraping (1.2 = 120% of market value)
    MAX_SCRAPE_PRICE_MULTIPLIER = 1.2
    
    def __init__(
        self,
        discount_threshold: float = 20.0,
        min_sold_samples: int = 5,
        recency_weight: float = 0.7
    ):
        """
        Initialize price analyzer
        
        Args:
            discount_threshold: Minimum discount % to flag as deal
            min_sold_samples: Minimum sold listings needed for reliable data
            recency_weight: Weight for recent sales (0-1, higher = more weight)
        """
        self.discount_threshold = discount_threshold
        self.min_sold_samples = min_sold_samples
        self.recency_weight = recency_weight
        logger.info(f"Price analyzer initialized (threshold: {discount_threshold}%)")
    
    def calculate_market_value(self, sold_listings: List[Dict]) -> Optional[Dict]:
        """
        Calculate market value statistics from sold listings
        
        Args:
            sold_listings: List of sold listing dictionaries
        
        Returns:
            Dictionary with market value statistics or None if insufficient data
        """
        if not sold_listings or len(sold_listings) < self.min_sold_samples:
            logger.warning(f"Insufficient sold listings: {len(sold_listings)} < {self.min_sold_samples}")
            return None
        
        # Extract prices
        prices = [listing['price'] for listing in sold_listings if listing['price'] > 0]
        
        if not prices:
            return None
        
        # Calculate basic statistics
        prices_array = np.array(prices)
        avg_price = float(np.mean(prices_array))
        median_price = float(np.median(prices_array))
        std_price = float(np.std(prices_array))
        min_price = float(np.min(prices_array))
        max_price = float(np.max(prices_array))
        
        # Calculate weighted average based on recency
        weighted_avg = self._calculate_weighted_average(sold_listings)
        
        # Determine market value (use weighted average if available, else regular average)
        market_value = weighted_avg if weighted_avg else avg_price
        
        return {
            'market_value': market_value,
            'average': avg_price,
            'median': median_price,
            'std_dev': std_price,
            'min': min_price,
            'max': max_price,
            'sample_size': len(prices),
            'weighted_average': weighted_avg
        }
    
    def _calculate_weighted_average(self, sold_listings: List[Dict]) -> Optional[float]:
        """
        Calculate weighted average price giving more weight to recent sales
        
        Args:
            sold_listings: List of sold listing dictionaries
        
        Returns:
            Weighted average price or None if dates not available
        """
        listings_with_dates = [
            listing for listing in sold_listings
            if listing.get('end_time') and listing['price'] > 0
        ]
        
        if not listings_with_dates:
            return None
        
        # Calculate weights based on recency
        now = datetime.now()
        weights = []
        prices = []
        
        for listing in listings_with_dates:
            end_time = listing['end_time']
            if end_time.tzinfo:
                # Make both timezone-aware or both naive
                end_time = end_time.replace(tzinfo=None)
            
            # Days ago
            days_ago = (now - end_time).days
            
            # Calculate weight (exponential decay based on recency_weight)
            weight = np.exp(-self.recency_weight * days_ago / 30)
            
            weights.append(weight)
            prices.append(listing['price'])
        
        if not weights:
            return None
        
        # Calculate weighted average
        weights_array = np.array(weights)
        prices_array = np.array(prices)
        weighted_avg = float(np.sum(prices_array * weights_array) / np.sum(weights_array))
        
        return weighted_avg
    
    def find_opportunities(
        self,
        active_listings: List[Dict],
        sold_listings: List[Dict]
    ) -> pd.DataFrame:
        """
        Compare active listings against market value to find deals
        
        Args:
            active_listings: List of active listing dictionaries
            sold_listings: List of sold listing dictionaries
        
        Returns:
            DataFrame with opportunities sorted by discount percentage
        """
        logger.info(f"Analyzing {len(active_listings)} active vs {len(sold_listings)} sold listings")
        
        # Calculate market value
        market_stats = self.calculate_market_value(sold_listings)
        
        if not market_stats:
            logger.warning("Cannot calculate market value - insufficient data")
            return pd.DataFrame()
        
        market_value = market_stats['market_value']
        logger.info(f"Market value: ${market_value:.2f}")
        
        # Analyze each active listing
        opportunities = []
        
        for listing in active_listings:
            if listing['price'] <= 0:
                continue
            
            # Calculate discount
            discount_pct = ((market_value - listing['price']) / market_value) * 100
            
            # Check if it meets threshold
            if discount_pct >= self.discount_threshold:
                potential_profit = market_value - listing['price']
                
                opportunities.append({
                    'title': listing['title'],
                    'active_price': listing['price'],
                    'market_value': market_value,
                    'avg_sold_price': market_stats['average'],
                    'median_sold_price': market_stats['median'],
                    'discount_pct': discount_pct,
                    'potential_profit': potential_profit,
                    'profit_margin': (potential_profit / listing['price']) * 100,
                    'url': listing['url'],
                    'image_url': listing['image_url'],
                    'condition': listing['condition'],
                    'seller': listing['seller_name'],
                    'listing_type': listing['listing_type'],
                    'sold_comps': market_stats['sample_size'],
                    'price_std_dev': market_stats['std_dev'],
                })
        
        # Create DataFrame
        if not opportunities:
            logger.info("No opportunities found")
            return pd.DataFrame()
        
        df = pd.DataFrame(opportunities)
        
        # Sort by discount percentage
        df = df.sort_values('discount_pct', ascending=False)
        
        logger.info(f"Found {len(df)} opportunities")
        
        return df
    
    def _is_sportscardpro_client(self, client) -> bool:
        """
        Check if the client is a Sports Card Pro client
        
        Args:
            client: API client instance
        
        Returns:
            True if Sports Card Pro client, False otherwise
        """
        # Import here to avoid circular dependency
        from src.sportscardpro_client import SportsCardProClient
        return isinstance(client, SportsCardProClient)
    
    def analyze_by_keyword(
        self,
        keywords: List[str],
        client,
        config: Dict
    ) -> Dict[str, pd.DataFrame]:
        """
        Analyze opportunities for multiple keywords
        
        Args:
            keywords: List of search keywords
            client: API client instance (eBay or Sports Card Pro)
            config: Configuration dictionary
        
        Returns:
            Dictionary mapping keywords to opportunity DataFrames
        """
        results = {}
        
        # Check if we're using Sports Card Pro client
        is_sportscardpro = self._is_sportscardpro_client(client)
        
        for keyword in keywords:
            logger.info(f"Analyzing keyword: {keyword}")
            
            try:
                if is_sportscardpro:
                    # Use Sports Card Pro API
                    opportunities = self._analyze_sportscardpro(keyword, client, config)
                else:
                    # Use eBay API (legacy)
                    # Search active listings
                    active_listings = client.search_active_listings(
                        keywords=keyword,
                        category_id=config.get('search', {}).get('categories', [None])[0],
                        min_price=config.get('filters', {}).get('min_price'),
                        max_price=config.get('filters', {}).get('max_price'),
                        condition=config.get('filters', {}).get('condition'),
                        listing_type=config.get('search', {}).get('listing_type', 'all'),
                        max_results=config.get('api', {}).get('max_results', 100)
                    )
                    
                    # Search sold listings
                    sold_listings = client.search_sold_listings(
                        keywords=keyword,
                        category_id=config.get('search', {}).get('categories', [None])[0],
                        days_back=config.get('analysis', {}).get('sold_days', 30),
                        min_price=config.get('filters', {}).get('min_price'),
                        max_price=config.get('filters', {}).get('max_price'),
                        max_results=config.get('api', {}).get('max_results', 100)
                    )
                    
                    # Find opportunities
                    opportunities = self.find_opportunities(active_listings, sold_listings)
                
                if not opportunities.empty:
                    results[keyword] = opportunities
                
            except Exception as e:
                logger.error(f"Failed to analyze keyword '{keyword}': {str(e)}")
                continue
        
        return results
    
    def _analyze_sportscardpro(
        self,
        keyword: str,
        client,
        config: Dict
    ) -> pd.DataFrame:
        """
        Analyze opportunities using Sports Card Pro API
        
        Args:
            keyword: Search keyword
            client: SportsCardProClient instance
            config: Configuration dictionary
        
        Returns:
            DataFrame with opportunities sorted by discount percentage
        """
        # Build simple search query from config filters
        query_parts = []
        
        # Add keyword
        if keyword and keyword.strip():
            query_parts.append(keyword.strip())
        
        # Add other filters from config to build a more specific query
        if config.get('search', {}).get('player'):
            query_parts.append(config['search']['player'])
        if config.get('search', {}).get('year'):
            query_parts.append(str(config['search']['year']))
        if config.get('search', {}).get('set'):
            query_parts.append(config['search']['set'])
        if config.get('search', {}).get('sport'):
            query_parts.append(config['search']['sport'])
        
        # Join all parts into a single query
        query = ' '.join(query_parts)
        
        if not query:
            logger.warning("Empty query generated from keyword and config")
            return pd.DataFrame()
        
        # Search for cards
        cards = client.search_cards(
            query=query,
            limit=config.get('api', {}).get('max_results', 20)
        )
        
        if not cards:
            logger.warning(f"No cards found for query: {query}")
            return pd.DataFrame()
        
        logger.info(f"Found {len(cards)} cards for query: {query}")
        
        # Analyze each card for opportunities
        opportunities = []
        
        for card in cards:
            try:
                # Get market value from Sports Card Pro
                market_value = card.get('market_value', 0)
                current_price = card.get('price', 0)
                
                if market_value <= 0 or current_price <= 0:
                    continue
                
                # Calculate discount
                discount_pct = ((market_value - current_price) / market_value) * 100
                
                # Check if it meets threshold
                if discount_pct >= self.discount_threshold:
                    # Get additional details if needed
                    card_id = card.get('card_id')
                    market_stats = None
                    
                    if card_id:
                        market_stats = client.get_market_value(card_id)
                    
                    potential_profit = market_value - current_price
                    
                    opportunities.append({
                        'title': card.get('title', 'Unknown Card'),
                        'active_price': current_price,
                        'market_value': market_value,
                        'avg_sold_price': market_stats.get('average', market_value) if market_stats else market_value,
                        'median_sold_price': market_stats.get('median', market_value) if market_stats else market_value,
                        'discount_pct': discount_pct,
                        'potential_profit': potential_profit,
                        'profit_margin': (potential_profit / current_price) * 100,
                        'url': f"https://www.sportscardspro.com/card/{card_id}" if card_id else '',
                        'image_url': card.get('image_url', ''),
                        'condition': f"{card.get('grading_company', '')} {card.get('grade', '')}".strip() or 'Raw',
                        'seller': 'Sports Card Pro',
                        'listing_type': 'Market Data',
                        'sold_comps': market_stats.get('sample_size', 0) if market_stats else 0,
                        'price_std_dev': market_stats.get('std_dev', 0) if market_stats else 0,
                        'player': card.get('player', ''),
                        'sport': card.get('sport', ''),
                        'year': card.get('year', ''),
                        'set': card.get('set', ''),
                        'card_number': card.get('card_number', ''),
                    })
                    
            except Exception as e:
                logger.warning(f"Failed to analyze card: {str(e)}")
                continue
        
        # Create DataFrame
        if not opportunities:
            logger.info(f"No opportunities found for query: {query}")
            return pd.DataFrame()
        
        df = pd.DataFrame(opportunities)
        
        # Sort by discount percentage
        df = df.sort_values('discount_pct', ascending=False)
        
        logger.info(f"Found {len(df)} opportunities for query: {query}")
        
        return df
    
    def analyze_with_scraping(
        self,
        sportscardpro_client,
        ebay_scraper,
        query: str
    ) -> Dict[str, List[Dict]]:
        """
        Find arbitrage opportunities using Sports Card Pro + eBay scraping
        
        Args:
            sportscardpro_client: Sports Card Pro API client
            ebay_scraper: eBay web scraper
            query: Search query
        
        Returns:
            Dictionary with opportunities
        """
        logger.info(f"Analyzing arbitrage for: {query}")
        
        opportunities = []
        
        # 1. Get market values from Sports Card Pro
        scp_cards = sportscardpro_client.search_cards(query=query, limit=10)  # Reduce to 10 to avoid too many eBay requests
        
        if not scp_cards:
            logger.warning(f"No Sports Card Pro data found for: {query}")
            return {'opportunities': []}
        
        # 2. Instead of searching eBay for each individual card,
        #    use the original query for eBay (which is already specific)
        logger.info(f"Scraping eBay with original query: {query}")
        
        ebay_listings = ebay_scraper.search_listings(
            query=query,
            limit=30
        )
        
        if not ebay_listings:
            logger.warning(f"No eBay listings found for: {query}")
            return {'opportunities': []}
        
        # 3. Compare eBay listings against Sports Card Pro market values
        #    Match by fuzzy string comparison of titles
        for listing in ebay_listings:
            listing_title = listing.get('title', '').lower()
            
            # Filter out non-sports cards
            if self._is_non_sports_card(listing_title):
                logger.debug(f"Skipping non-sports card: {listing_title}")
                continue
            
            # Try to match listing to Sports Card Pro cards
            best_match = None
            best_match_score = 0
            
            for scp_card in scp_cards:
                match_score = self._calculate_match_score(listing, scp_card)
                
                if match_score > best_match_score:
                    best_match_score = match_score
                    best_match = scp_card
            
            # If we found a reasonable match, compare prices
            if best_match and best_match_score > 0.3:  # 30% match threshold
                market_value = best_match.get('market_value', 0)
                
                if market_value == 0:
                    continue
                
                listing_price = listing.get('total_cost', 0)
                
                if listing_price == 0:
                    continue
                
                # Calculate discount
                discount_pct = ((market_value - listing_price) / market_value) * 100
                
                if discount_pct >= self.discount_threshold:
                    logger.info(f"eBay listing: {listing_title[:80]}")
                    logger.info(f"Best match: {best_match.get('title', '')} (score: {best_match_score:.2f})")
                    logger.info(f"Market value: ${market_value:.2f}, Listing price: ${listing_price:.2f}")
                    
                    opportunities.append({
                        'listing': listing,
                        'market_data': best_match,
                        'market_value': market_value,
                        'listing_price': listing_price,
                        'discount_pct': discount_pct,
                        'potential_profit': market_value - listing_price,
                        'match_score': best_match_score,
                        'query': query
                    })
        
        # Sort by discount percentage
        opportunities.sort(key=lambda x: x['discount_pct'], reverse=True)
        
        logger.info(f"Found {len(opportunities)} opportunities for: {query}")
        
        return {'opportunities': opportunities}
    
    def get_summary_stats(self, opportunities_df: pd.DataFrame) -> Dict:
        """
        Calculate summary statistics for opportunities
        
        Args:
            opportunities_df: DataFrame of opportunities
        
        Returns:
            Dictionary with summary statistics
        """
        if opportunities_df.empty:
            return {
                'total_deals': 0,
                'avg_discount': 0.0,
                'total_potential_profit': 0.0,
                'avg_potential_profit': 0.0,
                'max_discount': 0.0,
                'max_profit': 0.0
            }
        
        return {
            'total_deals': len(opportunities_df),
            'avg_discount': float(opportunities_df['discount_pct'].mean()),
            'total_potential_profit': float(opportunities_df['potential_profit'].sum()),
            'avg_potential_profit': float(opportunities_df['potential_profit'].mean()),
            'max_discount': float(opportunities_df['discount_pct'].max()),
            'max_profit': float(opportunities_df['potential_profit'].max())
        }
    
    def _is_non_sports_card(self, title: str) -> bool:
        """
        Check if listing is NOT a sports card
        
        Args:
            title: Listing title (lowercase)
        
        Returns:
            True if NOT a sports card
        """
        non_card_keywords = [
            'funko', 'pop', 'vinyl', 'figure',
            'magic the gathering', 'mtg', 'magic card',
            'pokemon', 'yugioh', 'yu-gi-oh',
            'video game', 'xbox', 'playstation', 'nintendo', 'switch',
            'comic book', 'graphic novel', 'paperback',
            'jersey', 'autograph photo', 'signed photo',
            'bobblehead', 'plush', 'toy',
        ]
        
        for keyword in non_card_keywords:
            if keyword in title:
                return True
        
        return False
    
    def _calculate_match_score(self, listing: Dict, scp_card: Dict) -> float:
        """
        Calculate how well an eBay listing matches a Sports Card Pro card
        
        Args:
            listing: eBay listing dict
            scp_card: Sports Card Pro card dict
        
        Returns:
            Match score from 0.0 to 1.0
        """
        listing_title = listing.get('title', '').lower()
        
        # Extract key components from Sports Card Pro card
        player = scp_card.get('player', '').lower()
        card_set = scp_card.get('set', '').lower()
        year = scp_card.get('year', '').lower()
        
        score = 0.0
        
        # Check for player name (most important)
        if player and player in listing_title:
            score += 0.5
        
        # Check for set name
        if card_set and any(word in listing_title for word in card_set.split()):
            score += 0.3
        
        # Check for year
        if year and year in listing_title:
            score += 0.2
        
        # Bonus: Check for card-specific terms
        card_terms = ['card', 'rookie', 'rc', 'prizm', 'chrome', 'topps', 'panini', 'fleer', 'psa', 'bgs']
        matching_terms = sum(1 for term in card_terms if term in listing_title)
        score += min(matching_terms * 0.05, 0.2)  # Up to 0.2 bonus
        
        return min(score, 1.0)  # Cap at 1.0
    
    def _build_ebay_query(self, user_query: str) -> str:
        """
        Build optimized eBay search query from user input
        
        Args:
            user_query: Original user search query
        
        Returns:
            Optimized eBay search string
        """
        query = user_query.strip()
        
        # Add "card" if not already present to filter out non-cards
        if 'card' not in query.lower() and 'rc' not in query.lower():
            query += " card"
        
        return query
