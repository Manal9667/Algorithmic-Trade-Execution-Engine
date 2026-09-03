"""
Data loading utilities for the execution optimizer.

Functions for generating synthetic orders and loading real market data.
"""

import numpy as np
import pandas as pd
from pathlib import Path

def generate_synthetic_orders(n_orders=1000, price_range=(99, 101)):
    """
    Generate synthetic orders for backtesting.
    
    Args:
        n_orders: Number of orders to generate
        price_range: (min_price, max_price) tuple
    
    Returns:
        pandas DataFrame with columns: id, side, type, price, qty
    
    Example:
        >>> df = generate_synthetic_orders(100)
        >>> print(df.head())
    """
    orders = []
    for i in range(n_orders):
        # Random side: 50% buy, 50% sell
        side = 'B' if np.random.random() < 0.5 else 'S'
        
        # Random type: 70% limit, 30% market
        order_type = 'market' if np.random.random() < 0.3 else 'limit'
        
        # Random price (only for limit orders)
        price = np.random.uniform(*price_range) if order_type == 'limit' else 0
        
        # Random quantity: 10-1000 shares
        qty = np.random.randint(10, 1000)
        
        orders.append({
            'id': i + 1,
            'side': side,
            'type': order_type,
            'price': price,
            'qty': qty
        })
    
    return pd.DataFrame(orders)

def load_real_data(filepath):
    """
    Load real market data from a CSV file.
    
    Expected columns: id, side, type, price, qty
    
    Args:
        filepath: Path to CSV file
    
    Returns:
        pandas DataFrame with market data
    
    Example:
        >>> df = load_real_data('market_data.csv')
    """
    return pd.read_csv(filepath)

def preprocess_orders(df):
    """
    Clean and standardize order data.
    
    Validates that required columns exist and data types are correct.
    
    Args:
        df: DataFrame with order data
    
    Returns:
        Cleaned DataFrame
    
    Raises:
        ValueError: If required columns are missing
    
    Example:
        >>> df = preprocess_orders(df)
    """
    # Check required columns
    required = ['id', 'side', 'type', 'price', 'qty']
    missing = [col for col in required if col not in df.columns]
    
    if missing:
        raise ValueError(f"Missing columns: {missing}. Required: {required}")
    
    # Validate data
    assert df['id'].dtype in [np.int64, np.int32, int], "id must be integer"
    assert df['qty'].dtype in [np.int64, np.int32, int], "qty must be integer"
    assert df['price'].dtype in [np.float64, np.float32, float], "price must be float"
    
    # Convert side to uppercase
    df = df.copy()
    df['side'] = df['side'].str.upper()
    
    # Validate side values
    assert all(df['side'].isin(['B', 'S'])), "side must be 'B' or 'S'"
    
    return df

if __name__ == "__main__":
    # Test: generate synthetic orders
    df = generate_synthetic_orders(100)
    print(f"Generated {len(df)} orders")
    print(df.head())
    
    # Test: preprocess
    df_clean = preprocess_orders(df)
    print(f"\nPreprocessed {len(df_clean)} orders")