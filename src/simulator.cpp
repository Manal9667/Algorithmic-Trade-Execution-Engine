#include "market.h"
#include <algorithm>
#include <cmath>
#include <iostream>

namespace {
constexpr uint64_t kSyntheticIdBase = 1000000000;
}

/**
 * MarketSimulator constructor
 */
MarketSimulator::MarketSimulator(double initial_price, const LiquidityModel& liq)
    : liquidity(liq), current_price(initial_price), rng(std::random_device{}()),
      next_synthetic_id(kSyntheticIdBase) {}

/**
 * evolve_price()
 *
 * Simulate price movement using random walk.
 *
 * Simple model (can upgrade to GBM):
 * price_new = price_old * (1 + drift + N(0, volatility))
 */
void MarketSimulator::evolve_price(double volatility, double drift) {
    std::normal_distribution<> dist(drift, volatility);
    double change = dist(rng);

    current_price *= (1.0 + change);

    if (current_price < 0.01) {
        current_price = 0.01;
    }
}

/**
 * refresh_synthetic_quotes()
 *
 * Keep the matching engine's inside quotes aligned with the current mid.
 * Previous synthetic liquidity is cancelled (if still resting) so stale
 * prices from earlier ticks cannot fill later strategy orders.
 */
void MarketSimulator::refresh_synthetic_quotes() {
    if (synthetic_bid_id != 0) {
        engine.cancel_order(synthetic_bid_id, OrderSide::Buy, synthetic_bid_price);
        synthetic_bid_id = 0;
    }
    if (synthetic_ask_id != 0) {
        engine.cancel_order(synthetic_ask_id, OrderSide::Sell, synthetic_ask_price);
        synthetic_ask_id = 0;
    }

    const uint64_t qty = liquidity.quoted_quantity();
    synthetic_bid_price = liquidity.quoted_bid(current_price);
    synthetic_ask_price = liquidity.quoted_ask(current_price);

    synthetic_bid_id = next_synthetic_id++;
    synthetic_ask_id = next_synthetic_id++;

    engine.submit_order(Order(
        synthetic_bid_id,
        OrderSide::Buy,
        OrderType::Limit,
        synthetic_bid_price,
        qty
    ));
    engine.submit_order(Order(
        synthetic_ask_id,
        OrderSide::Sell,
        OrderType::Limit,
        synthetic_ask_price,
        qty
    ));
}

/**
 * run_backtest()
 *
 * Each tick:
 *  1. Evolve the mid price
 *  2. Quote bid/ask and size from the current mid and liquidity model
 *  3. Snapshot that market state
 *  4. Submit the next strategy order against those quotes
 */
void MarketSimulator::run_backtest(
    const std::vector<Order>& orders,
    int num_ticks,
    double volatility
) {
    double drift = 0.0;
    size_t order_idx = 0;

    for (int tick = 0; tick < num_ticks; ++tick) {
        evolve_price(volatility, drift);
        refresh_synthetic_quotes();

        const uint64_t qty = liquidity.quoted_quantity();
        snapshots.push_back({
            current_price,
            synthetic_bid_price,
            synthetic_ask_price,
            qty,
            qty,
            static_cast<uint64_t>(tick * 100)
        });

        if (order_idx < orders.size()) {
            engine.submit_order(orders[order_idx]);
            ++order_idx;
        }
    }
}

/**
 * calculate_slippage()
 *
 * How much worse did you execute than the arrival price?
 *
 * Formula: (execution_price - arrival_price) / arrival_price
 */
double MarketSimulator::calculate_slippage(double arrival_price, double avg_exec_price) const {
    if (arrival_price == 0) return 0;
    return (avg_exec_price - arrival_price) / arrival_price;
}

/**
 * calculate_market_impact()
 *
 * How much did the market move due to your trades?
 *
 * Formula: (final_price - initial_mid) / initial_mid
 */
double MarketSimulator::calculate_market_impact(double initial_mid, const std::vector<Trade>& trades) const {
    if (trades.empty()) return 0;
    double final_mid = current_price;
    return (final_mid - initial_mid) / initial_mid;
}
