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
    
    def analyze_by_keyword(
        self,
        keywords: List[str],
        ebay_client,
        config: Dict
    ) -> Dict[str, pd.DataFrame]:
        """
        Analyze opportunities for multiple keywords
        
        Args:
            keywords: List of search keywords
            ebay_client: eBayClient instance
            config: Configuration dictionary
        
        Returns:
            Dictionary mapping keywords to opportunity DataFrames
        """
        results = {}
        
        for keyword in keywords:
            logger.info(f"Analyzing keyword: {keyword}")
            
            try:
                # Search active listings
                active_listings = ebay_client.search_active_listings(
                    keywords=keyword,
                    category_id=config.get('search', {}).get('categories', [None])[0],
                    min_price=config.get('filters', {}).get('min_price'),
                    max_price=config.get('filters', {}).get('max_price'),
                    condition=config.get('filters', {}).get('condition'),
                    listing_type=config.get('search', {}).get('listing_type', 'all'),
                    max_results=config.get('api', {}).get('max_results', 100)
                )
                
                # Search sold listings
                sold_listings = ebay_client.search_sold_listings(
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
