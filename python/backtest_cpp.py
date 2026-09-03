"""
Backtest using the C++ engine via Python bindings.

This script demonstrates how to:
1. Import the C++ executor module
2. Create orders programmatically
3. Run backtests through the C++ matching engine
4. Analyze results in Python
"""

import sys
import os
import numpy as np
import pandas as pd

# Add build directory to Python path so we can import the executor module
# Adjust this path to wherever your build/ folder is
build_dir = os.path.join(os.path.dirname(__file__), '..', 'build', 'Release')
if os.path.exists(build_dir):
    sys.path.insert(0, build_dir)
elif os.path.exists(os.path.join(os.path.dirname(__file__), '..', 'build')):
    # Try without Release suffix
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'build'))

try:
    from executor import (
        MatchingEngine, Order, OrderSide, OrderType,
        LiquidityModel, MarketSimulator
    )
except ImportError as e:
    print(f"Error importing executor module: {e}")
    print(f"Make sure you've built Phase 4 and added the build path correctly")
    sys.exit(1)

class CPPBacktest:
    """
    Backtest harness using the C++ engine via Python bindings.
    
    Example usage:
        >>> bt = CPPBacktest()
        >>> trades = bt.run_orders(orders_data)
        >>> bt.analyze(trades)
    """
    
    def __init__(self, initial_price=100.0):
        """
        Initialize backtest.
        
        Args:
            initial_price: Starting price for the market
        """
        self.initial_price = initial_price
        self.engine = MatchingEngine()
        self.liquidity = LiquidityModel(0.01, 1000, 0.0001)
    
    def run_orders(self, orders_data):
        """
        Execute orders through the C++ matching engine.
        
        Args:
            orders_data: List of dicts with keys:
                - side: 'B' or 'S'
                - type: 'market' or 'limit'
                - price: limit price (0 for market)
                - qty: quantity
        
        Returns:
            List of Trade objects from C++
        
        Example:
            >>> orders = [
            ...     {'side': 'S', 'type': 'limit', 'price': 100.0, 'qty': 100},
            ...     {'side': 'B', 'type': 'market', 'price': 0, 'qty': 100},
            ... ]
            >>> trades = bt.run_orders(orders)
        """
        all_trades = []
        
        for i, order_data in enumerate(orders_data):
            # Convert Python data to C++ Order object
            side = OrderSide.Buy if order_data['side'] == 'B' else OrderSide.Sell
            order_type = OrderType.Market if order_data['type'] == 'market' else OrderType.Limit
            price = order_data['price']
            qty = order_data['qty']
            
            # Create and submit order to C++ engine
            order = Order(i + 1, side, order_type, price, qty)
            fills = self.engine.submit_order(order)
            
            # Collect trades
            all_trades.extend(fills)
        
        return all_trades
    
    def analyze(self, trades):
        """
        Analyze execution results.
        
        Args:
            trades: List of Trade objects from C++
        """
        if not trades:
            print("No trades executed")
            return
        
        # Extract data from Trade objects
        prices = [t.price for t in trades]
        quantities = [t.qty for t in trades]
        
        print(f"Total trades: {len(trades)}")
        print(f"Total quantity: {sum(quantities)}")
        print(f"Average price: ${np.mean(prices):.4f}")
        print(f"Min price: ${min(prices):.4f}")
        print(f"Max price: ${max(prices):.4f}")
        
        # Calculate slippage
        avg_exec = np.mean(prices)
        slippage = (avg_exec - self.initial_price) / self.initial_price * 100
        print(f"Slippage: {slippage:.2f}%")
        
        return {
            'num_trades': len(trades),
            'total_qty': sum(quantities),
            'avg_price': np.mean(prices),
            'slippage_pct': slippage
        }

def test_simple_backtest():
    """
    Test 1: Simple market order backtest
    
    Setup:
    - Add sell order at $100
    - Submit market buy for same qty
    - Should fill completely
    """
    print("=" * 60)
    print("TEST 1: Simple Market Order")
    print("=" * 60)
    
    bt = CPPBacktest(initial_price=100.0)
    
    # Orders: first add sell, then buy
    orders = [
        {'side': 'S', 'type': 'limit', 'price': 100.0, 'qty': 100},
        {'side': 'B', 'type': 'market', 'price': 0, 'qty': 100},
    ]
    
    trades = bt.run_orders(orders)
    print(f"\nExecuted {len(trades)} trade(s)")
    for trade in trades:
        print(f"  Buy {trade.qty} from seller @ ${trade.price:.2f}")
    
    result = bt.analyze(trades)
    print()

def test_partial_fill_backtest():
    """
    Test 2: Partial fill across price levels
    
    Setup:
    - Add sell orders at $100 (50 shares) and $100.50 (100 shares)
    - Submit market buy for 120 shares
    - Should fill 50 @ $100, then 70 @ $100.50
    """
    print("=" * 60)
    print("TEST 2: Partial Fill Across Price Levels")
    print("=" * 60)
    
    bt = CPPBacktest(initial_price=100.0)
    
    # Orders: build order book, then buy
    orders = [
        {'side': 'S', 'type': 'limit', 'price': 100.0, 'qty': 50},
        {'side': 'S', 'type': 'limit', 'price': 100.5, 'qty': 100},
        {'side': 'B', 'type': 'market', 'price': 0, 'qty': 120},
    ]
    
    trades = bt.run_orders(orders)
    print(f"\nExecuted {len(trades)} trade(s):")
    for i, trade in enumerate(trades, 1):
        print(f"  Trade {i}: Buy {trade.qty} @ ${trade.price:.2f}")
    
    result = bt.analyze(trades)
    print()

def test_limit_order_backtest():
    """
    Test 3: Limit order that doesn't cross
    
    Setup:
    - Seller asking $100.50
    - Buyer bidding only $100.00
    - Should not fill, order rests on book
    """
    print("=" * 60)
    print("TEST 3: Limit Order (No Cross)")
    print("=" * 60)
    
    bt = CPPBacktest(initial_price=100.0)
    
    # Orders: sell at 100.50, buy limit at 100.00 (no cross)
    orders = [
        {'side': 'S', 'type': 'limit', 'price': 100.50, 'qty': 100},
        {'side': 'B', 'type': 'limit', 'price': 100.00, 'qty': 100},
    ]
    
    trades = bt.run_orders(orders)
    print(f"\nExecuted {len(trades)} trade(s) (expected 0)")
    
    if len(trades) == 0:
        print("✓ Correct: Buy limit order rested on book (didn't cross)")
    
    result = bt.analyze(trades)
    print()

def test_realistic_scenario():
    """
    Test 4: More realistic scenario with multiple orders
    """
    print("=" * 60)
    print("TEST 4: Realistic Multi-Order Scenario")
    print("=" * 60)
    
    bt = CPPBacktest(initial_price=100.0)
    
    # Build initial order book
    orders = [
        # Initial book: sellers
        {'side': 'S', 'type': 'limit', 'price': 100.0, 'qty': 100},
        {'side': 'S', 'type': 'limit', 'price': 100.5, 'qty': 150},
        {'side': 'S', 'type': 'limit', 'price': 101.0, 'qty': 200},
        
        # Initial book: buyers
        {'side': 'B', 'type': 'limit', 'price': 99.5, 'qty': 100},
        {'side': 'B', 'type': 'limit', 'price': 99.0, 'qty': 150},
        
        # Now execute: market buy 250 shares
        {'side': 'B', 'type': 'market', 'price': 0, 'qty': 250},
    ]
    
    trades = bt.run_orders(orders)
    print(f"\nExecuted {len(trades)} trade(s):")
    for i, trade in enumerate(trades, 1):
        print(f"  Trade {i}: Buy {trade.qty} @ ${trade.price:.2f}")
    
    result = bt.analyze(trades)
    print()

if __name__ == "__main__":
    print("\n")
    print("╔" + "=" * 58 + "╗")
    print("║" + " " * 58 + "║")
    print("║" + "  PHASE 4: C++ Engine Backtest via Python Bindings".center(58) + "║")
    print("║" + " " * 58 + "║")
    print("╚" + "=" * 58 + "╝")
    print()
    
    try:
        test_simple_backtest()
        test_partial_fill_backtest()
        test_limit_order_backtest()
        test_realistic_scenario()
        
        print("=" * 60)
        print("✓ All backtest tests completed successfully!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n✗ Error running backtest: {e}")
        import traceback
        traceback.print_exc()