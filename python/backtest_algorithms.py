"""
Comprehensive backtest comparing TWAP vs VWAP vs Naive execution.

This is the research/analysis phase where we measure real cost savings.
"""

import sys
import os
import numpy as np
import pandas as pd
from collections import defaultdict

# Import C++ modules
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
except ImportError as e:
    print(f"Error: Cannot import C++ executor module: {e}")
    print("Make sure you've built Phase 4 with Python bindings.")
    sys.exit(1)

from algorithms import (
    NaiveExecutor, TWAPExecutor, VWAPExecutor, compare_algorithms, print_comparison
)

def scenario_1_basic():
    """
    Scenario 1: Basic execution - tight spread, good liquidity
    
    Setup: Seller at $100, buyer wants to buy 1000 shares
    Expected: All algorithms should perform similarly
    """
    print("\n" + "=" * 80)
    print("SCENARIO 1: Basic Execution (Tight Spread, Good Liquidity)")
    print("=" * 80)
    
    engine = MatchingEngine()
    
    # Add lots of liquidity
    for i in range(100, 102):
        price = i
        qty = 1000
        engine.submit_order(Order(1000 + int(price * 100), OrderSide.Sell, OrderType.Limit, price, qty))
    
    results = compare_algorithms(engine, 100.0, 1000, num_slices=10)
    print_comparison(results)
    
    return results

def scenario_2_wide_spread():
    """
    Scenario 2: Wide spread, low liquidity
    
    Setup: Wide bid-ask spread, limited shares at each level
    Expected: TWAP/VWAP should reduce slippage by spreading execution
    """
    print("\n" + "=" * 80)
    print("SCENARIO 2: Wide Spread, Low Liquidity")
    print("=" * 80)
    
    engine = MatchingEngine()
    
    # Wide spread: asks from 99.9 to 101.0
    prices = [99.9, 100.0, 100.1, 100.2, 100.3, 100.5, 100.8, 101.0]
    for i, price in enumerate(prices):
        # Only 100 shares at each level (low liquidity)
        engine.submit_order(Order(1000 + i, OrderSide.Sell, OrderType.Limit, price, 100))
    
    results = compare_algorithms(engine, 100.0, 500, num_slices=5)
    print_comparison(results)
    
    return results

def scenario_3_volume_shape():
    """
    Scenario 3: Volume has a shape (U-shaped)
    
    Setup: More volume at edges (opening/closing), less in middle
    Expected: VWAP should adapt better than TWAP
    """
    print("\n" + "=" * 80)
    print("SCENARIO 3: Volume Concentration (U-Shaped)")
    print("=" * 80)
    
    engine = MatchingEngine()
    
    # U-shaped volume: more at edges
    volume_levels = [300, 200, 150, 150, 200, 300]
    for i, (price, vol) in enumerate(zip(np.linspace(99.7, 100.3, len(volume_levels)), volume_levels)):
        engine.submit_order(Order(1000 + i, OrderSide.Sell, OrderType.Limit, price, vol))
    
    results = compare_algorithms(engine, 100.0, 1000, num_slices=6)
    print_comparison(results)
    
    return results

def scenario_4_huge_order():
    """
    Scenario 4: Huge order vs small liquidity (stress test)
    
    Setup: Want to buy 10,000 shares but only 500 per price level
    Expected: Slippage should be significant, TWAP/VWAP should help
    """
    print("\n" + "=" * 80)
    print("SCENARIO 4: Huge Order Relative to Liquidity")
    print("=" * 80)
    
    engine = MatchingEngine()
    
    # Small quantities at many price levels
    for i in range(50):
        price = 100.0 + (i * 0.01)
        engine.submit_order(Order(1000 + i, OrderSide.Sell, OrderType.Limit, price, 200))
    
    results = compare_algorithms(engine, 100.0, 5000, num_slices=20)
    print_comparison(results)
    
    return results

def scenario_5_realistic_market():
    """
    Scenario 5: Realistic market microstructure
    
    Setup: Real order book shape with typical spreads
    Expected: All three algorithms should work well
    """
    print("\n" + "=" * 80)
    print("SCENARIO 5: Realistic Market Microstructure")
    print("=" * 80)
    
    engine = MatchingEngine()
    
    # Build realistic book: pyramid shape
    # More volume at mid, less at edges
    base_volume = 500
    for i in range(10):
        # Asks
        price = 100.0 + (i * 0.02)
        volume = base_volume * (1.0 - (i / 20.0))  # Decreasing volume
        engine.submit_order(Order(1000 + i, OrderSide.Sell, OrderType.Limit, price, max(int(volume), 50)))
    
    results = compare_algorithms(engine, 100.0, 2000, num_slices=10)
    print_comparison(results)
    
    return results

def run_all_scenarios():
    """Run all test scenarios and summarize"""
    print("\n")
    print("╔" + "=" * 78 + "╗")
    print("║" + " " * 78 + "║")
    print("║" + "  PHASE 5: Execution Algorithm Comparison".center(78) + "║")
    print("║" + " " * 78 + "║")
    print("╚" + "=" * 78 + "╝")
    
    all_results = {}
    
    all_results['scenario_1'] = scenario_1_basic()
    all_results['scenario_2'] = scenario_2_wide_spread()
    all_results['scenario_3'] = scenario_3_volume_shape()
    all_results['scenario_4'] = scenario_4_huge_order()
    all_results['scenario_5'] = scenario_5_realistic_market()
    
    # Summary
    print("\n" + "=" * 80)
    print("OVERALL SUMMARY")
    print("=" * 80)
    
    algo_costs = defaultdict(list)
    algo_slippage = defaultdict(list)
    
    for scenario, results in all_results.items():
        for result in results:
            algo_costs[result.name].append(result.total_cost)
            algo_slippage[result.name].append(result.slippage_pct)
    
    print("\nAverage Cost by Algorithm:")
    for algo in ['Naive', 'TWAP', 'VWAP']:
        if algo in algo_costs:
            avg_cost = np.mean(algo_costs[algo])
            avg_slippage = np.mean(algo_slippage[algo])
            print(f"  {algo:<10}: ${avg_cost:>12,.2f} (avg slippage: {avg_slippage:>6.2f}%)")
    
    # Calculate improvement
    if 'Naive' in algo_costs and 'VWAP' in algo_costs:
        naive_cost = np.mean(algo_costs['Naive'])
        vwap_cost = np.mean(algo_costs['VWAP'])
        improvement = ((naive_cost - vwap_cost) / naive_cost) * 100
        print(f"\n✓ VWAP beats Naive by average: {improvement:.1f}%")
    
    print("\n" + "=" * 80)
    print("✓ All scenarios completed!")
    print("=" * 80)

if __name__ == "__main__":
    try:
        run_all_scenarios()
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)