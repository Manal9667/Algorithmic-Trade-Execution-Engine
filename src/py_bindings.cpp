#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include "engine.h"
#include "market.h"
#include "execution.h"

namespace py = pybind11;

/**
 * PYBIND11_MODULE
 * 
 * This macro creates a Python module called "executor".
 * It exports all C++ classes so they can be used from Python.
 * 
 * Usage from Python:
 *   from executor import MatchingEngine, Order, OrderSide, OrderType
 *   engine = MatchingEngine()
 *   order = Order(1, OrderSide.Buy, OrderType.Limit, 100.0, 100)
 *   trades = engine.submit_order(order)
 */
PYBIND11_MODULE(executor, m) {
    m.doc() = "High-performance order matching engine";
    
    // ========================================================================
    // ENUMS
    // ========================================================================
    
    /**
     * OrderType enum: Market or Limit
     */
    py::enum_<OrderType>(m, "OrderType")
        .value("Market", OrderType::Market)
        .value("Limit", OrderType::Limit)
        .export_values();
    
    /**
     * OrderSide enum: Buy or Sell
     */
    py::enum_<OrderSide>(m, "OrderSide")
        .value("Buy", OrderSide::Buy)
        .value("Sell", OrderSide::Sell)
        .export_values();
    
    // ========================================================================
    // STRUCTS
    // ========================================================================
    
    /**
     * Order struct
     * 
     * Python usage:
     *   order = Order(1, OrderSide.Buy, OrderType.Limit, 100.0, 100)
     *   print(order.id, order.price, order.qty, order.remaining())
     */
    py::class_<Order>(m, "Order")
        .def(py::init<uint64_t, OrderSide, OrderType, double, uint64_t>())
        .def_readwrite("id", &Order::id)
        .def_readwrite("side", &Order::side)
        .def_readwrite("type", &Order::type)
        .def_readwrite("price", &Order::price)
        .def_readwrite("qty", &Order::qty)
        .def_readwrite("filled", &Order::filled)
        .def("remaining", &Order::remaining)
        .def("is_filled", &Order::is_filled);
    
    /**
     * Trade struct
     * 
     * Python usage:
     *   print(f"Trade: {trade.buy_order_id} bought from {trade.sell_order_id}")
     *   print(f"Price: ${trade.price:.2f}, Qty: {trade.qty}")
     */
    py::class_<Trade>(m, "Trade")
        .def(py::init<uint64_t, uint64_t, double, uint64_t>())
        .def_readwrite("buy_order_id", &Trade::buy_order_id)
        .def_readwrite("sell_order_id", &Trade::sell_order_id)
        .def_readwrite("price", &Trade::price)
        .def_readwrite("qty", &Trade::qty);

    py::class_<BookLevel>(m, "BookLevel")
        .def(py::init<>())
        .def_readwrite("price", &BookLevel::price)
        .def_readwrite("qty", &BookLevel::qty);
    
    /**
     * MarketSnapshot struct
     */
    py::class_<MarketSnapshot>(m, "MarketSnapshot")
        .def(py::init<>())
        .def_readwrite("last_price", &MarketSnapshot::last_price)
        .def_readwrite("mid_price", &MarketSnapshot::mid_price)
        .def_readwrite("bid", &MarketSnapshot::bid)
        .def_readwrite("ask", &MarketSnapshot::ask)
        .def_readwrite("bid_volume", &MarketSnapshot::bid_volume)
        .def_readwrite("ask_volume", &MarketSnapshot::ask_volume)
        .def_readwrite("volume", &MarketSnapshot::volume)
        .def_readwrite("bar_volume", &MarketSnapshot::bar_volume)
        .def_readwrite("timestamp_ms", &MarketSnapshot::timestamp_ms)
        .def_readwrite("bids", &MarketSnapshot::bids)
        .def_readwrite("asks", &MarketSnapshot::asks);

    py::class_<VectorMarketSource>(m, "VectorMarketSource")
        .def(py::init<std::vector<MarketState>>())
        .def("next", &VectorMarketSource::next)
        .def("reset", &VectorMarketSource::reset);

    py::class_<RealtimeMarketSource>(m, "RealtimeMarketSource")
        .def(py::init<>())
        .def("publish", &RealtimeMarketSource::publish)
        .def("next", &RealtimeMarketSource::next)
        .def("reset", &RealtimeMarketSource::reset);

    py::class_<CsvMarketSource>(m, "CsvMarketSource")
        .def(py::init<std::string>())
        .def("next", &CsvMarketSource::next)
        .def("reset", &CsvMarketSource::reset)
        .def("ok", &CsvMarketSource::ok);

    py::class_<ExecutionFill>(m, "ExecutionFill")
        .def_readonly("trade", &ExecutionFill::trade)
        .def_readonly("timestamp_ms", &ExecutionFill::timestamp_ms)
        .def_readonly("bid", &ExecutionFill::bid)
        .def_readonly("ask", &ExecutionFill::ask)
        .def_readonly("market_volume", &ExecutionFill::market_volume);

    py::class_<ExecutionResult>(m, "ExecutionResult")
        .def_readonly("requested_quantity", &ExecutionResult::requested_quantity)
        .def_readonly("filled_quantity", &ExecutionResult::filled_quantity)
        .def_readonly("arrival_price", &ExecutionResult::arrival_price)
        .def_readonly("average_execution_price", &ExecutionResult::average_execution_price)
        .def_readonly("market_vwap", &ExecutionResult::market_vwap)
        .def_readonly("fill_rate", &ExecutionResult::fill_rate)
        .def_readonly("slippage", &ExecutionResult::slippage)
        .def_readonly("implementation_shortfall", &ExecutionResult::implementation_shortfall)
        .def_readonly("vwap_deviation", &ExecutionResult::vwap_deviation)
        .def_readonly("completion_time_ms", &ExecutionResult::completion_time_ms)
        .def_readonly("fills", &ExecutionResult::fills);

    py::class_<ExecutionSession>(m, "ExecutionSession")
        .def(py::init<>())
        .def("run", &ExecutionSession::run)
        .def("engine", &ExecutionSession::engine, py::return_value_policy::reference_internal);
    
    // ========================================================================
    // CLASSES
    // ========================================================================
    
    /**
     * OrderBook class
     * 
     * Python usage:
     *   book = OrderBook()
     *   book.add_order(order)
     *   best_bid = book.best_bid()  # Returns optional (None if empty)
     */
    py::class_<OrderBook>(m, "OrderBook")
        .def(py::init<>())
        .def("add_order", &OrderBook::add_order)
        .def("best_bid", &OrderBook::best_bid)
        .def("best_ask", &OrderBook::best_ask)
        .def("mid_price", &OrderBook::mid_price)
        .def("volume_at", &OrderBook::volume_at)
        .def("cancel_order", &OrderBook::cancel_order)
        .def("print_state", &OrderBook::print_state);
    
    /**
     * MatchingEngine class
     * 
     * Main class for matching orders.
     * 
     * Python usage:
     *   engine = MatchingEngine()
     *   trades = engine.submit_order(order)
     *   all_trades = engine.get_all_trades()
     *   print(f"Total trades: {engine.get_trade_count()}")
     */
    py::class_<MatchingEngine>(m, "MatchingEngine")
        .def(py::init<>())
        .def("submit_order", &MatchingEngine::submit_order)
        .def("cancel_order", &MatchingEngine::cancel_order)
        .def("match_market", &MatchingEngine::match_market)
        .def("match_limit", &MatchingEngine::match_limit)
        .def("get_book", &MatchingEngine::get_book, py::return_value_policy::reference_internal)
        .def("get_all_trades", &MatchingEngine::get_all_trades, py::return_value_policy::reference_internal)
        .def("get_trade_count", &MatchingEngine::get_trade_count);
    
    /**
     * LiquidityModel class
     * 
     * Python usage:
     *   liq = LiquidityModel(0.01, 1000, 0.0001)  # spread, volume, widening
     *   ask = liq.get_ask_for_qty(100.0, 500)     # mid=100, qty=500
     */
    py::class_<LiquidityModel>(m, "LiquidityModel")
        .def(py::init<double, double, double>())
        .def_readwrite("base_spread", &LiquidityModel::base_spread)
        .def_readwrite("liquidity_at_level", &LiquidityModel::liquidity_at_level)
        .def_readwrite("spread_widening", &LiquidityModel::spread_widening)
        .def("get_ask_for_qty", &LiquidityModel::get_ask_for_qty)
        .def("get_bid_for_qty", &LiquidityModel::get_bid_for_qty)
        .def("quoted_bid", &LiquidityModel::quoted_bid)
        .def("quoted_ask", &LiquidityModel::quoted_ask)
        .def("quoted_quantity", &LiquidityModel::quoted_quantity);
    
    /**
     * MarketSimulator class
     * 
     * Simulates a market with realistic prices and liquidity.
     * 
     * Python usage:
     *   liq = LiquidityModel(0.01, 1000, 0.0001)
     *   sim = MarketSimulator(100.0, liq)
     *   sim.run_backtest(orders, 10, 0.01)  # 10 ticks, 1% vol
     *   trades = sim.get_engine().get_all_trades()
     */
    py::class_<MarketSimulator>(m, "MarketSimulator")
        .def(py::init<double, const LiquidityModel&>())
        .def("run_backtest", &MarketSimulator::run_backtest)
        .def("get_engine", &MarketSimulator::get_engine, py::return_value_policy::reference_internal)
        .def("get_current_price", &MarketSimulator::get_current_price)
        .def("get_snapshots", &MarketSimulator::get_snapshots)
        .def("snapshot_source", &MarketSimulator::snapshot_source)
        .def("calculate_slippage", &MarketSimulator::calculate_slippage)
        .def("calculate_market_impact", &MarketSimulator::calculate_market_impact);
}