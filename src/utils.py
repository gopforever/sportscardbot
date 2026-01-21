"""Utility functions for the Sports Card Bot"""

import logging
import time
from functools import wraps
from typing import Callable, Any
from datetime import datetime, timedelta

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def rate_limit(calls_per_minute: int = 50):
    """
    Decorator to rate limit function calls
    
    Args:
        calls_per_minute: Maximum number of calls allowed per minute
    """
    min_interval = 60.0 / calls_per_minute
    last_called = [0.0]
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            elapsed = time.time() - last_called[0]
            left_to_wait = min_interval - elapsed
            if left_to_wait > 0:
                time.sleep(left_to_wait)
            ret = func(*args, **kwargs)
            last_called[0] = time.time()
            return ret
        return wrapper
    return decorator


def retry_on_failure(max_retries: int = 3, delay: float = 1.0):
    """
    Decorator to retry function on failure
    
    Args:
        max_retries: Maximum number of retry attempts
        delay: Delay between retries in seconds
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_retries - 1:
                        logger.error(f"Failed after {max_retries} attempts: {str(e)}")
                        raise
                    logger.warning(f"Attempt {attempt + 1} failed: {str(e)}. Retrying...")
                    time.sleep(delay * (attempt + 1))
            return None
        return wrapper
    return decorator


def format_currency(amount: float) -> str:
    """Format a number as currency"""
    return f"${amount:,.2f}"


def calculate_percentage_difference(price1: float, price2: float) -> float:
    """
    Calculate percentage difference between two prices
    
    Args:
        price1: First price (typically active listing)
        price2: Second price (typically market value)
    
    Returns:
        Percentage difference (negative means price1 is lower)
    """
    if price2 == 0:
        return 0.0
    return ((price1 - price2) / price2) * 100


def is_cache_valid(cache_time: datetime, cache_duration_minutes: int) -> bool:
    """
    Check if cached data is still valid
    
    Args:
        cache_time: When the data was cached
        cache_duration_minutes: How long cache is valid in minutes
    
    Returns:
        True if cache is still valid
    """
    if cache_time is None:
        return False
    return datetime.now() - cache_time < timedelta(minutes=cache_duration_minutes)


def clean_price(price_str: str) -> float:
    """
    Clean and convert price string to float
    
    Args:
        price_str: Price string (e.g., "$123.45")
    
    Returns:
        Float value of price
    """
    if not price_str:
        return 0.0
    
    # Remove currency symbols and commas
    cleaned = price_str.replace('$', '').replace(',', '').strip()
    
    try:
        return float(cleaned)
    except ValueError:
        logger.warning(f"Could not parse price: {price_str}")
        return 0.0


def truncate_text(text: str, max_length: int = 100) -> str:
    """
    Truncate text to maximum length
    
    Args:
        text: Input text
        max_length: Maximum length
    
    Returns:
        Truncated text with ellipsis if needed
    """
    if len(text) <= max_length:
        return text
    return text[:max_length - 3] + "..."
