#include "execution.h"

#include <algorithm>

ExecutionResult ExecutionSession::run(
    MarketDataSource& source,
    const std::vector<Order>& child_orders,
    double arrival_price
) {
    ExecutionResult result;
    result.arrival_price = arrival_price;
    for (const auto& order : child_orders) {
        result.requested_quantity += order.qty;
    }

    source.reset();
    engine_.clear_book();
    MarketState state;
    size_t order_index = 0;
    double market_value = 0.0;
    uint64_t market_quantity = 0;
    uint64_t previous_cumulative_volume = 0;

    while (source.next(state)) {
        normalize_market_state(state);
        engine_.clear_book();
        uint64_t level_id = 4000000000ULL;
        for (const auto& level : state.bids) {
            engine_.submit_order(Order(level_id++, OrderSide::Buy, OrderType::Limit,
                                       level.price, level.qty));
        }
        for (const auto& level : state.asks) {
            engine_.submit_order(Order(level_id++, OrderSide::Sell, OrderType::Limit,
                                       level.price, level.qty));
        }

        const uint64_t event_volume = state.bar_volume > 0
            ? state.bar_volume
            : state.volume >= previous_cumulative_volume
                ? state.volume - previous_cumulative_volume
                : 0;
        previous_cumulative_volume = state.volume;
        if (event_volume > 0 && state.last_price > 0.0) {
            market_value += state.last_price * event_volume;
            market_quantity += event_volume;
        }

        if (order_index >= child_orders.size()) {
            continue;
        }
        const auto& order = child_orders[order_index++];
        const auto trades = engine_.submit_order(order);
        for (const auto& trade : trades) {
            result.filled_quantity += trade.qty;
            result.fills.push_back({trade, state.timestamp_ms, state.bid, state.ask, event_volume});
        }
        if (!trades.empty()) {
            result.completion_time_ms = state.timestamp_ms;
        }
    }

    double execution_value = 0.0;
    for (const auto& fill : result.fills) {
        execution_value += fill.trade.price * fill.trade.qty;
    }
    if (result.filled_quantity > 0) {
        result.average_execution_price = execution_value / result.filled_quantity;
    }
    if (market_quantity > 0) {
        result.market_vwap = market_value / market_quantity;
    }
    if (result.requested_quantity > 0) {
        result.fill_rate = static_cast<double>(result.filled_quantity) /
                           result.requested_quantity;
    }
    if (arrival_price != 0.0 && result.filled_quantity > 0) {
        result.slippage = (result.average_execution_price - arrival_price) / arrival_price;
        result.implementation_shortfall =
            (result.average_execution_price - arrival_price) * result.filled_quantity;
    }
    if (result.market_vwap != 0.0 && result.filled_quantity > 0) {
        result.vwap_deviation =
            (result.average_execution_price - result.market_vwap) / result.market_vwap;
    }
    return result;
}