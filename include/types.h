#ifndef EXECUTOR_TYPES_H
#define EXECUTOR_TYPES_H

#include <cstdint>
#include <string>
#include <vector>

enum class OrderType { Market, Limit };
enum class OrderSide { Buy = 'B', Sell = 'S' };

struct Order {
    uint64_t id; // Unique order ID
    OrderSide side; // Buy or sell
    OrderType type; // Market or limit
    double price; // Limit price (0 for market)
    uint64_t qty; // Quantity
    uint64_t filled = 0; // Amount filled
    
    Order(uint64_t id, OrderSide side, OrderType type, double price, uint64_t qty)
        : id(id), side(side), type(type), price(price), qty(qty) {}

    uint64_t remaining() const{
        return qty - filled;
    }

    bool is_filled() const{
        return filled >= qty;
    }
};

struct Trade {
    uint64_t buy_order_id;
    uint64_t sell_order_id;
    double price;
    uint64_t qty;
    Trade(uint64_t buy_id, uint64_t sell_id, double price, uint64_t qty)
        : buy_order_id(buy_id), sell_order_id(sell_id), price(price), qty(qty) {}
};

/**
 * One price level on either side of the book.
 * Used by the matching engine and by every market-data source.
 */
struct BookLevel {
    double price = 0.0;
    uint64_t qty = 0;
};

#endif

