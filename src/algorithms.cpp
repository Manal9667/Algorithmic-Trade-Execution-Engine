#include "algorithms.h"
#include <numeric>

/**
 * TWAPAlgorithm::generate_orders()
 * 
 * Split order evenly: qty1 = qty2 = ... = qty_n = total_qty / num_slices
 * 
 * Remainder is added to first slice to ensure total = total_qty
 * 
 * Time complexity: O(num_slices)
 */
std::vector<Order> TWAPAlgorithm::generate_orders(
    uint64_t parent_order_id,
    OrderSide side,
    uint64_t total_qty,
    double limit_price,
    int num_slices
) {
    std::vector<Order> orders;
    
    // Calculate slice size
    uint64_t slice_qty = total_qty / num_slices;
    uint64_t remainder = total_qty % num_slices;
    
    for (int i = 0; i < num_slices; ++i) {
        // Add remainder to first slice
        uint64_t qty = slice_qty + (i == 0 ? remainder : 0);
        
        // Create child order
        // ID format: parent_id * 1000 + slice_index
        uint64_t child_id = parent_order_id * 1000 + i;
        
        Order child(child_id, side, OrderType::Limit, limit_price, qty);
        orders.push_back(child);
    }
    
    return orders;
}

/**
 * VWAPAlgorithm::generate_orders()
 * 
 * Split order based on volume profile.
 * Each slice gets: qty_i = total_qty * profile[i]
 * 
 * If profile[i] = 0.3, then slice i gets 30% of total
 * If no profile set, use uniform (same as TWAP)
 * 
 * Time complexity: O(num_slices)
 */
std::vector<Order> VWAPAlgorithm::generate_orders(
    uint64_t parent_order_id,
    OrderSide side,
    uint64_t total_qty,
    double limit_price,
    int num_slices
) {
    std::vector<Order> orders;

    // If no profile, use uniform (default to TWAP behavior)
    if (volume_profile.empty()) {
        uint64_t slice_qty = total_qty / num_slices;
        uint64_t remainder = total_qty % num_slices;

        for (int i = 0; i < num_slices; ++i) {
            uint64_t qty = slice_qty + (i == 0 ? remainder : 0);

            uint64_t child_id = parent_order_id * 1000 + i;
            Order child(
                child_id,
                side,
                OrderType::Limit,
                limit_price,
                qty
            );

            orders.push_back(child);
        }

        return orders;
    }

    // Only use as many profile buckets as there are requested slices.
    size_t num_profile_slices = std::min(
        volume_profile.size(),
        static_cast<size_t>(num_slices)
    );

    // Normalize only the profile buckets we are actually using.
    double total_profile_volume = 0.0;

    for (size_t i = 0; i < num_profile_slices; ++i) {
        total_profile_volume += volume_profile[i];
    }

    uint64_t total_assigned = 0;

    for (size_t i = 0; i < num_profile_slices; ++i) {

        // Convert the profile value into a normalized fraction.
        double fraction =
            volume_profile[i] / total_profile_volume;

        uint64_t qty = static_cast<uint64_t>(
            total_qty * fraction
        );

        // Give the final slice any remaining quantity caused by
        // integer rounding.
        if (i == num_profile_slices - 1) {
            qty = total_qty - total_assigned;
        }

        total_assigned += qty;

        uint64_t child_id = parent_order_id * 1000 + i;

        Order child(
            child_id,
            side,
            OrderType::Limit,
            limit_price,
            qty
        );

        orders.push_back(child);
    }

    return orders;
}


/**
 * AdaptiveAlgorithm::generate_orders()
 * 
 * Placeholder for advanced adaptive algorithm.
 * For now, defaults to TWAP behavior.
 * 
 * In real implementation, this would:
 * - Monitor real-time market data
 * - Adjust execution based on current conditions
 * - React to price movements and volume spikes
 */
std::vector<Order> AdaptiveAlgorithm::generate_orders(
    uint64_t parent_order_id,
    OrderSide side,
    uint64_t total_qty,
    double limit_price,
    int num_slices
) {
    // For now, use TWAP as baseline
    TWAPAlgorithm twap;
    return twap.generate_orders(parent_order_id, side, total_qty, limit_price, num_slices);
}