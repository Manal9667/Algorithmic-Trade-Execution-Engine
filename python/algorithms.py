"""
Python implementations of execution algorithms.

Wraps the C++ algorithms and provides analysis.
"""

import sys
import os
import numpy as np
from dataclasses import dataclass

# Try to import C++ executor module
build_dir = os.path.join(os.path.dirname(__file__), '..', 'build', 'Release')
if os.path.exists(build_dir):
    sys.path.insert(0, build_dir)
elif os.path.exists(os.path.join(os.path.dirname(__file__), '..', 'build')):
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'build'))

try:
    from executor import (
        MatchingEngine, Order, OrderSide, OrderType,
        LiquidityModel, MarketSimulator
    )
    CPP_AVAILABLE = True
except ImportError:
    CPP_AVAILABLE = False

@dataclass
class AlgorithmResult:
    """Result of running an execution algorithm"""
    name: str
    trades: list
    total_quantity: int
    avg_price: float
    slippage_pct: float
    total_cost: float
    num_trades: int

class TWAPExecutor:
    """
    Time-Weighted Average Price executor
    
    Splits order into equal slices and executes one per time period.
    """
    
    def execute(self, engine, initial_price, qty, num_slices=10, limit_price=None):
        """
        Execute a TWAP order through the engine.
        
        Args:
            engine: MatchingEngine instance
            initial_price: Arrival price (for slippage calculation)
            qty: Total quantity to execute
            num_slices: Number of time slices
            limit_price: Limit price (None = market)
        
        Returns:
            AlgorithmResult with execution details
        """
        slice_qty = qty // num_slices
        remainder = qty % num_slices
        
        trades = []
        execution_prices = []
        
        for i in range(num_slices):
            # Add remainder to first slice
            order_qty = slice_qty + (remainder if i == 0 else 0)
            
            if limit_price is None:
                order_type = OrderType.Market
                price = 0
            else:
                order_type = OrderType.Limit
                price = limit_price
            
            # Create and submit order
            order = Order(i + 1000, OrderSide.Buy, order_type, price, order_qty)
            fills = engine.submit_order(order)
            trades.extend(fills)
            
            # Track execution prices
            for fill in fills:
                execution_prices.append(fill.price)
        
        # Calculate metrics
        avg_price = np.mean(execution_prices) if execution_prices else initial_price
        total_cost = sum(t.price * t.qty for t in trades)
        slippage = (avg_price - initial_price) / initial_price * 100
        
        return AlgorithmResult(
            name="TWAP",
            trades=trades,
            total_quantity=sum(t.qty for t in trades),
            avg_price=avg_price,
            slippage_pct=slippage,
            total_cost=total_cost,
            num_trades=len(trades)
        )

class VWAPExecutor:
    """
    Volume-Weighted Average Price executor
    
    Executes in proportion to market volume for better prices.
    """
    
    def execute(self, engine, initial_price, qty, volume_profile=None, num_slices=10, limit_price=None):
        """
        Execute a VWAP order through the engine.
        
        Args:
            engine: MatchingEngine instance
            initial_price: Arrival price
            qty: Total quantity
            volume_profile: List of volume fractions (should sum to 1)
            num_slices: Number of slices
            limit_price: Limit price (None = market)
        
        Returns:
            AlgorithmResult with execution details
        """
        if volume_profile is None:
            # Default to uniform (same as TWAP)
            volume_profile = [1.0 / num_slices] * num_slices
        
        # Normalize profile
        total_profile = sum(volume_profile)
        volume_profile = [v / total_profile for v in volume_profile]
        
        trades = []
        execution_prices = []
        
        for i, fraction in enumerate(volume_profile[:num_slices]):
            order_qty = int(qty * fraction)
            if order_qty == 0:
                continue
            
            if limit_price is None:
                order_type = OrderType.Market
                price = 0
            else:
                order_type = OrderType.Limit
                price = limit_price
            
            # Create and submit order
            order = Order(i + 2000, OrderSide.Buy, order_type, price, order_qty)
            fills = engine.submit_order(order)
            trades.extend(fills)
            
            # Track prices
            for fill in fills:
                execution_prices.append(fill.price)
        
        # Calculate metrics
        avg_price = np.mean(execution_prices) if execution_prices else initial_price
        total_cost = sum(t.price * t.qty for t in trades)
        slippage = (avg_price - initial_price) / initial_price * 100
        
        return AlgorithmResult(
            name="VWAP",
            trades=trades,
            total_quantity=sum(t.qty for t in trades),
            avg_price=avg_price,
            slippage_pct=slippage,
            total_cost=total_cost,
            num_trades=len(trades)
        )

class NaiveExecutor:
    """
    Naive execution: single market order
    
    Baseline for comparison. Expected to have worst prices.
    """
    
    def execute(self, engine, initial_price, qty):
        """
        Execute a single market order.
        
        Args:
            engine: MatchingEngine instance
            initial_price: Arrival price
            qty: Total quantity
        
        Returns:
            AlgorithmResult
        """
        order = Order(5000, OrderSide.Buy, OrderType.Market, 0, qty)
        trades = engine.submit_order(order)
        
        if not trades:
            return AlgorithmResult(
                name="Naive",
                trades=[],
                total_quantity=0,
                avg_price=initial_price,
                slippage_pct=0,
                total_cost=0,
                num_trades=0
            )
        
        execution_prices = [t.price for t in trades]
        avg_price = np.mean(execution_prices)
        total_cost = sum(t.price * t.qty for t in trades)
        slippage = (avg_price - initial_price) / initial_price * 100
        
        return AlgorithmResult(
            name="Naive",
            trades=trades,
            total_quantity=sum(t.qty for t in trades),
            avg_price=avg_price,
            slippage_pct=slippage,
            total_cost=total_cost,
            num_trades=len(trades)
        )

def compare_algorithms(engine, initial_price, qty, num_slices=10):
    """
    Run all algorithms and compare results.
    
    Args:
        engine: MatchingEngine instance
        initial_price: Arrival price
        qty: Quantity to execute
        num_slices: Time slices for TWAP/VWAP
    
    Returns:
        List of AlgorithmResult objects
    """
    results = []
    
    # Run naive
    naive = NaiveExecutor()
    results.append(naive.execute(engine, initial_price, qty))
    
    # Run TWAP
    twap = TWAPExecutor()
    results.append(twap.execute(engine, initial_price, qty, num_slices))
    
    # Run VWAP with front-loaded profile (more volume early)
    vwap = VWAPExecutor()
    # Front-loaded: 40%, 30%, 20%, 10% pattern
    profile = [0.4, 0.3, 0.2, 0.1]
    # Extend for more slices if needed
    while len(profile) < num_slices:
        profile.append(0.01)  # Small amount for remaining slices
    
    results.append(vwap.execute(engine, initial_price, qty, profile, num_slices))
    
    return results

def print_comparison(results):
    """Print nicely formatted comparison of algorithms"""
    print("\n" + "=" * 80)
    print(f"{'Algorithm':<15} {'Avg Price':<15} {'Slippage %':<15} {'Total Cost':<15} {'Num Trades':<15}")
    print("=" * 80)
    
    for result in results:
        print(
            f"{result.name:<15} "
            f"${result.avg_price:<14.4f} "
            f"{result.slippage_pct:<14.2f}% "
            f"${result.total_cost:<14.2f} "
            f"{result.num_trades:<15}"
        )
    
    print("=" * 80)
    
    # Calculate savings
    if len(results) > 1:
        baseline = results[0]
        print("\nCost Savings vs Naive:")
        for result in results[1:]:
            savings = baseline.total_cost - result.total_cost
            savings_pct = (savings / baseline.total_cost) * 100 if baseline.total_cost > 0 else 0
            print(f"  {result.name}: ${savings:.2f} ({savings_pct:.2f}%)")

if __name__ == "__main__":
    if not CPP_AVAILABLE:
        print("C++ executor module not available. Build Phase 4 first.")
        sys.exit(1)
    
    print("Testing Python algorithm classes...")
    
    # Create a simple scenario
    engine = MatchingEngine()
    
    # Build realistic order book
    print("Building order book...")
    for i, price in enumerate(np.linspace(99.5, 100.5, 20)):
        if price < 100:
            # Bids
            engine.submit_order(Order(i, OrderSide.Buy, OrderType.Limit, price, 100))
        else:
            # Asks
            engine.submit_order(Order(i + 100, OrderSide.Sell, OrderType.Limit, price, 100))
    
    # Run comparison
    results = compare_algorithms(engine, 100.0, 1000, num_slices=5)
    print_comparison(results)
    print("\n✓ Algorithm test complete!")