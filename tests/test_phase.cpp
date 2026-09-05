#include "../include/execution.h"
#include "../include/algorithms.h"
#include "../include/market.h"
#include <cassert>
#include <fstream>
#include <iostream>

void test_vector_source_and_session() {
    VectorMarketSource source({
        {100.0, 0.0, 99.0, 100.0, 100, 100, 1000, 100, 1, {{99.0, 100}}, {{100.0, 100}, {100.5, 200}}},
        {100.0, 0.0, 99.0, 100.0, 100, 100, 1200, 200, 2, {{99.0, 100}}, {{100.0, 100}, {100.5, 200}}}
    });
    TWAPAlgorithm twap;
    const auto orders = twap.generate_orders(10, OrderSide::Buy, 250, 1000.0, 2);

    ExecutionSession session;
    const auto result = session.run(source, orders, 99.5);
    assert(result.requested_quantity == 250);
    assert(result.filled_quantity == 200);
    assert(result.fills.size() == 2);
    assert(result.fills[0].trade.price == 100.0);
    assert(result.fills[1].trade.price == 100.5);
    assert(result.completion_time_ms == 2);
    assert(result.fill_rate == 0.8);
    assert(result.market_vwap == (100.0 * 100.0 + 100.0 * 200.0) / 300.0);
}

void test_csv_source() {
    const std::string path = "phase_market_test.csv";
    {
        std::ofstream file(path);
        file << "timestamp_ms,last,bid,ask,bid_size,ask_size,volume,bar_volume,bid_depth,ask_depth\n";
        file << "10,100,99.5,100.5,50,75,20,20,99.5:50|99:100,100.5:75|101:125\n";
    }
    CsvMarketSource source(path);
    MarketState state;
    assert(source.ok());
    assert(source.next(state));
    assert(state.mid_price == 100.0);
    assert(state.asks.size() == 2);
    assert(state.asks[1].qty == 125);
    assert(!source.next(state));
    source.reset();
    assert(source.next(state));
    std::remove(path.c_str());
}

void test_invalid_algorithm_inputs() {
    TWAPAlgorithm twap;
    VWAPAlgorithm vwap;
    assert(twap.generate_orders(1, OrderSide::Buy, 100, 100.0, 0).empty());
    assert(vwap.generate_orders(1, OrderSide::Buy, 100, 100.0, -1).empty());
    vwap.set_volume_profile({0.0, -1.0});
    const auto orders = vwap.generate_orders(1, OrderSide::Buy, 100, 100.0, 2);
    assert(orders.size() == 2);
    assert(orders[0].qty + orders[1].qty == 100);
}

void test_synthetic_snapshots_are_replayable() {
    MarketSimulator simulator(100.0, LiquidityModel(0.02, 100, 0.0), 7);
    simulator.run_backtest({}, 2, 0.0);
    auto source = simulator.snapshot_source();
    MarketState state;
    assert(source.next(state));
    assert(state.bid == 99.99);
    assert(state.ask == 100.01);
    assert(state.bids.size() == 1);
    assert(state.asks.size() == 1);
}

void test_realtime_source_requires_ordered_events() {
    RealtimeMarketSource source;
    MarketState first;
    first.timestamp_ms = 20;
    first.bid = 99.0;
    first.ask = 101.0;
    assert(source.publish(first));
    MarketState late = first;
    late.timestamp_ms = 10;
    assert(!source.publish(late));
    MarketState out;
    assert(source.next(out));
    assert(out.mid_price == 100.0);
}

int main() {
    test_vector_source_and_session();
    test_csv_source();
    test_invalid_algorithm_inputs();
    test_synthetic_snapshots_are_replayable();
    test_realtime_source_requires_ordered_events();
    std::cout << "Phase source/session tests passed\n";
    return 0;
}