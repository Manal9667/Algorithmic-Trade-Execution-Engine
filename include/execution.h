#ifndef EXECUTOR_EXECUTION_H
#define EXECUTOR_EXECUTION_H

#include "engine.h"
#include "market_data.h"
#include <vector>

struct ExecutionFill {
    Trade trade;
    uint64_t timestamp_ms = 0;
    double bid = 0.0;
    double ask = 0.0;
    uint64_t market_volume = 0;
};

struct ExecutionResult {
    uint64_t requested_quantity = 0;
    uint64_t filled_quantity = 0;
    double arrival_price = 0.0;
    double average_execution_price = 0.0;
    double market_vwap = 0.0;
    double fill_rate = 0.0;
    double slippage = 0.0;
    double implementation_shortfall = 0.0;
    double vwap_deviation = 0.0;
    uint64_t completion_time_ms = 0;
    std::vector<ExecutionFill> fills;
};

class ExecutionSession {
public:
    ExecutionResult run(
        MarketDataSource& source,
        const std::vector<Order>& child_orders,
        double arrival_price
    );

    const MatchingEngine& engine() const { return engine_; }

private:
    MatchingEngine engine_;
};

#endif