#ifndef EXECUTOR_ALGORITHMS_H
#define EXECUTOR_ALGORITHMS_H

#include "types.h"
#include "engine.h"
#include <vector>
#include <memory>
#include <string>
#include <cmath>

/**
 * ExecutionAlgorithm
 * 
 * Base class for execution algorithms.
 * An algorithm takes a parent order and generates child orders to execute it.
 * 
 * Example: TWAP splits 1000 shares into 10 orders of 100 shares each.
 */
class ExecutionAlgorithm {
public:
    virtual ~ExecutionAlgorithm() = default;
    
    /**
     * Generate child orders for execution
     * 
     * Args:
     *   parent_order_id: ID of the parent order
     *   side: Buy or Sell
     *   total_qty: Total quantity to execute
     *   limit_price: Price limit (0 for market)
     *   num_slices: Number of child orders to create
     * 
     * Returns:
     *   Vector of Order objects ready to submit
     */
    virtual std::vector<Order> generate_orders(
        uint64_t parent_order_id,
        OrderSide side,
        uint64_t total_qty,
        double limit_price,
        int num_slices
    ) = 0;
    
    /**
     * Get algorithm name
     */
    virtual std::string name() const = 0;
};

/**
 * TWAPAlgorithm
 * 
 * Time-Weighted Average Price
 * 
 * Strategy: Split order into equal-sized slices and submit one per time period.
 * Goal: Minimize market impact by spreading execution over time.
 * 
 * Example:
 *   Want to buy 1000 shares
 *   Split into 10 slices of 100 shares each
 *   Submit one slice per minute
 *   Avg execution price = VWAP-ish (but time-based, not volume-based)
 * 
 * Advantages:
 *   - Simple to understand and implement
 *   - Predictable execution schedule
 *   - Good baseline algorithm
 * 
 * Disadvantages:
 *   - Ignores market volume
 *   - May execute when liquidity is low
 */
class TWAPAlgorithm : public ExecutionAlgorithm {
public:
    /**
     * Generate time-weighted child orders
     * 
     * Divides total_qty equally across num_slices
     * Each order is a limit order at the specified price
     */
    std::vector<Order> generate_orders(
        uint64_t parent_order_id,
        OrderSide side,
        uint64_t total_qty,
        double limit_price,
        int num_slices
    ) override;
    
    std::string name() const override { return "TWAP"; }
};

/**
 * VWAPAlgorithm
 * 
 * Volume-Weighted Average Price
 * 
 * Strategy: Execute in proportion to expected market volume.
 * Executes more when volume is high, less when volume is low.
 * Goal: Better execution prices by following natural volume patterns.
 * 
 * Example:
 *   Expected volume profile: [0.3, 0.2, 0.2, 0.15, 0.15]
 *   Total order: 1000 shares
 *   Slice 1: 300 shares (30% of volume)
 *   Slice 2: 200 shares (20% of volume)
 *   etc.
 * 
 * Advantages:
 *   - Better prices (follows natural volume)
 *   - Lower market impact
 *   - Professional algorithm (widely used)
 * 
 * Disadvantages:
 *   - Requires volume forecast
 *   - More complex to implement
 *   - Sensitive to volume forecast accuracy
 */
class VWAPAlgorithm : public ExecutionAlgorithm {
private:
    std::vector<double> volume_profile;  // Expected volume at each time bucket
    
public:
    /**
     * Set the volume profile (expected volume at each time bucket)
     * 
     * Profile values should sum to 1.0 (they are fractions)
     * 
     * Example:
     *   [0.4, 0.3, 0.2, 0.1]  // More volume early, less later
     */
    void set_volume_profile(const std::vector<double>& profile) {
        volume_profile = profile;
    }
    
    /**
     * Generate volume-weighted child orders
     * 
     * If no profile set, defaults to uniform (same as TWAP)
     */
    std::vector<Order> generate_orders(
        uint64_t parent_order_id,
        OrderSide side,
        uint64_t total_qty,
        double limit_price,
        int num_slices
    ) override;
    
    std::string name() const override { return "VWAP"; }
};

/**
 * AdaptiveAlgorithm (placeholder for Phase 5+)
 * 
 * Advanced strategy that adapts execution based on:
 * - Current market conditions
 * - Real-time volume
 * - Price movement
 * - Remaining time
 * 
 * Example:
 *   If price is falling, accelerate buys
 *   If price is rising, slow down buys
 *   If volume is high, increase execution
 *   If time is running out, execute faster
 */
class AdaptiveAlgorithm : public ExecutionAlgorithm {
public:
    std::vector<Order> generate_orders(
        uint64_t parent_order_id,
        OrderSide side,
        uint64_t total_qty,
        double limit_price,
        int num_slices
    ) override;
    
    std::string name() const override { return "Adaptive"; }
};

#endif