#include "../include/book.h"
#include <iostream>
#include <iomanip>

/**
 * Demo: Order Book in Action
 * 
 * This shows how to use the order book:
 * 1. Create buy and sell orders
 * 2. Add them to the book
 * 3. Query prices and volumes
 * 4. Cancel an order
 */
int main() {
    std::cout << "=== Order Book Demo ===" << std::endl << std::endl;
    
    // Create an order book
    OrderBook book;
    
    // ========================================================================
    // Step 1: Add some buy orders (bids)
    // ========================================================================
    std::cout << "Adding buy orders..." << std::endl;
    book.add_order({1, OrderSide::Buy, OrderType::Limit, 99.50, 100});
    book.add_order({2, OrderSide::Buy, OrderType::Limit, 99.00, 200});
    book.add_order({3, OrderSide::Buy, OrderType::Limit, 100.00, 150});
    std::cout << "Added 3 buy orders" << std::endl << std::endl;
    
    // ========================================================================
    // Step 2: Add some sell orders (asks)
    // ========================================================================
    std::cout << "Adding sell orders..." << std::endl;
    book.add_order({4, OrderSide::Sell, OrderType::Limit, 100.50, 100});
    book.add_order({5, OrderSide::Sell, OrderType::Limit, 101.00, 200});
    book.add_order({6, OrderSide::Sell, OrderType::Limit, 100.00, 150});
    std::cout << "Added 3 sell orders" << std::endl << std::endl;
    
    // ========================================================================
    // Step 3: Print current state
    // ========================================================================
    book.print_state();
    
    // ========================================================================
    // Step 4: Query prices
    // ========================================================================
    std::cout << "Querying prices:" << std::endl;
    if (auto bid = book.best_bid()) {
        std::cout << "  Best bid (highest buy price): $" << std::fixed << std::setprecision(2) << *bid << std::endl;
    }
    if (auto ask = book.best_ask()) {
        std::cout << "  Best ask (lowest sell price): $" << std::fixed << std::setprecision(2) << *ask << std::endl;
    }
    if (auto mid = book.mid_price()) {
        std::cout << "  Mid price (average): $" << std::fixed << std::setprecision(2) << *mid << std::endl;
    }
    std::cout << std::endl;
    
    // ========================================================================
    // Step 5: Query volumes at specific prices
    // ========================================================================
    std::cout << "Volumes at each price level:" << std::endl;
    
    std::cout << "  Buy side (bids):" << std::endl;
    std::cout << "    @ $100.00: " << book.volume_at(100.0, OrderSide::Buy) << " shares" << std::endl;
    std::cout << "    @ $99.50: " << book.volume_at(99.5, OrderSide::Buy) << " shares" << std::endl;
    std::cout << "    @ $99.00: " << book.volume_at(99.0, OrderSide::Buy) << " shares" << std::endl;
    
    std::cout << "  Sell side (asks):" << std::endl;
    std::cout << "    @ $100.00: " << book.volume_at(100.0, OrderSide::Sell) << " shares" << std::endl;
    std::cout << "    @ $100.50: " << book.volume_at(100.5, OrderSide::Sell) << " shares" << std::endl;
    std::cout << "    @ $101.00: " << book.volume_at(101.0, OrderSide::Sell) << " shares" << std::endl;
    std::cout << std::endl;
    
    // ========================================================================
    // Step 6: Cancel an order
    // ========================================================================
    std::cout << "Cancelling order #3 (100 shares @ $100.00 bid)..." << std::endl;
    bool cancelled = book.cancel_order(3, OrderSide::Buy, 100.0);
    if (cancelled) {
        std::cout << "✓ Order cancelled successfully" << std::endl;
    } else {
        std::cout << "✗ Order not found" << std::endl;
    }
    std::cout << std::endl;
    
    // ========================================================================
    // Step 7: Show state after cancellation
    // ========================================================================
    std::cout << "Book state after cancellation:" << std::endl;
    book.print_state();
    
    // ========================================================================
    // Step 8: Try to cancel a non-existent order
    // ========================================================================
    std::cout << "Attempting to cancel order #999 (doesn't exist)..." << std::endl;
    bool not_cancelled = book.cancel_order(999, OrderSide::Buy, 100.0);
    if (not_cancelled) {
        std::cout << "✓ Order cancelled" << std::endl;
    } else {
        std::cout << "✗ Order not found (expected)" << std::endl;
    }
    std::cout << std::endl;
    
    // ========================================================================
    // Done
    // ========================================================================
    std::cout << "Demo complete!" << std::endl;
    return 0;
}