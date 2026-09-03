#include "../include/types.h"
#include "../include/book.h"
#include "../include/engine.h"
#include "../include/algorithms.h"
#include "../include/market.h"
#include <iostream>
#include <chrono>
#include <vector>
#include <iomanip>
#include <random>

/**
 * Benchmarking utilities for the execution optimizer
 * 
 * Measures:
 * - Order book insertion/query performance
 * - Matching engine throughput
 * - Algorithm order generation
 * - End-to-end backtest speed
 */

class Benchmark {
private:
    std::mt19937 rng{std::random_device{}()};
    
public:
    /**
     * Measure execution time in milliseconds
     */
    template<typename Func>
    double measure_ms(Func f) {
        auto start = std::chrono::high_resolution_clock::now();
        f();
        auto end = std::chrono::high_resolution_clock::now();
        return std::chrono::duration<double, std::milli>(end - start).count();
    }
    
    /**
     * Benchmark 1: Order book insertion performance
     * 
     * Measures: How fast can we add orders to the book?
     * Expected: ~1 million insertions per second
     */
    void benchmark_order_book_insertion() {
        std::cout << "\n" << std::string(70, '=') << std::endl;
        std::cout << "BENCHMARK 1: Order Book Insertion" << std::endl;
        std::cout << std::string(70, '=') << std::endl;
        
        OrderBook book;
        const int num_orders = 100000;
        
        double time_ms = measure_ms([&]() {
            for (int i = 0; i < num_orders; ++i) {
                double price = 100.0 + (i % 100) * 0.01;
                Order o(i, OrderSide::Buy, OrderType::Limit, price, 100);
                book.add_order(o);
            }
        });
        
        double ops_per_sec = (num_orders / time_ms) * 1000;
        
        std::cout << "Orders inserted: " << num_orders << std::endl;
        std::cout << "Time: " << std::fixed << std::setprecision(2) << time_ms << " ms" << std::endl;
        std::cout << "Throughput: " << std::scientific << ops_per_sec << " ops/sec" << std::endl;
        std::cout << "Per operation: " << (time_ms / num_orders) * 1000 << " µs" << std::endl;
    }
    
    /**
     * Benchmark 2: Order book best price queries
     * 
     * Measures: How fast are queries for best bid/ask?
     * Expected: ~100 million queries per second (O(1) operation)
     */
    void benchmark_order_book_queries() {
        std::cout << "\n" << std::string(70, '=') << std::endl;
        std::cout << "BENCHMARK 2: Order Book Queries" << std::endl;
        std::cout << std::string(70, '=') << std::endl;
        
        OrderBook book;
        
        // Populate with orders
        for (int i = 0; i < 10000; ++i) {
            double price = 100.0 + (i % 100) * 0.01;
            Order o(i, OrderSide::Buy, OrderType::Limit, price, 100);
            book.add_order(o);
        }
        
        const int num_queries = 10000000;
        
        double time_ms = measure_ms([&]() {
            for (int i = 0; i < num_queries; ++i) {
                auto bid = book.best_bid();
                auto ask = book.best_ask();
                (void)bid; (void)ask;  // Prevent compiler optimization
            }
        });
        
        double queries_per_sec = (num_queries / time_ms) * 1000;
        
        std::cout << "Queries executed: " << num_queries << std::endl;
        std::cout << "Time: " << std::fixed << std::setprecision(2) << time_ms << " ms" << std::endl;
        std::cout << "Throughput: " << std::scientific << queries_per_sec << " queries/sec" << std::endl;
        std::cout << "Per query: " << (time_ms / num_queries) * 1e6 << " ns" << std::endl;
    }
    
    /**
     * Benchmark 3: Order matching throughput
     * 
     * Measures: How many orders can the matching engine process?
     * Expected: ~1 million matches per second
     */
    void benchmark_matching_engine() {
        std::cout << "\n" << std::string(70, '=') << std::endl;
        std::cout << "BENCHMARK 3: Matching Engine" << std::endl;
        std::cout << std::string(70, '=') << std::endl;
        
        MatchingEngine engine;
        const int num_orders = 100000;
        
        double time_ms = measure_ms([&]() {
            // Add sell orders first
            for (int i = 0; i < num_orders / 2; ++i) {
                Order o(i, OrderSide::Sell, OrderType::Limit, 100.0, 1);
                engine.submit_order(o);
            }
            
            // Then add matching buy orders (will all fill)
            for (int i = num_orders / 2; i < num_orders; ++i) {
                Order o(i, OrderSide::Buy, OrderType::Limit, 100.0, 1);
                engine.submit_order(o);
            }
        });
        
        double ops_per_sec = (num_orders / time_ms) * 1000;
        auto trade_count = engine.get_trade_count();
        
        std::cout << "Orders submitted: " << num_orders << std::endl;
        std::cout << "Trades generated: " << trade_count << std::endl;
        std::cout << "Time: " << std::fixed << std::setprecision(2) << time_ms << " ms" << std::endl;
        std::cout << "Order throughput: " << std::scientific << ops_per_sec << " orders/sec" << std::endl;
        std::cout << "Trade throughput: " << (trade_count / time_ms) * 1000 << " trades/sec" << std::endl;
    }
    
    /**
     * Benchmark 4: Algorithm order generation
     * 
     * Measures: How fast can we split an order?
     * Expected: ~1 million splits per second
     */
    void benchmark_algorithms() {
        std::cout << "\n" << std::string(70, '=') << std::endl;
        std::cout << "BENCHMARK 4: Algorithm Order Generation" << std::endl;
        std::cout << std::string(70, '=') << std::endl;
        
        TWAPAlgorithm twap;
        VWAPAlgorithm vwap;
        const int num_iterations = 10000;
        
        // TWAP benchmark
        double twap_time = measure_ms([&]() {
            for (int i = 0; i < num_iterations; ++i) {
                auto orders = twap.generate_orders(i, OrderSide::Buy, 1000000, 100.0, 100);
                (void)orders;
            }
        });
        
        // VWAP benchmark
        std::vector<double> profile = {0.4, 0.3, 0.2, 0.1};
        vwap.set_volume_profile(profile);
        
        double vwap_time = measure_ms([&]() {
            for (int i = 0; i < num_iterations; ++i) {
                auto orders = vwap.generate_orders(i, OrderSide::Buy, 1000000, 100.0, 100);
                (void)orders;
            }
        });
        
        std::cout << "Iterations: " << num_iterations << std::endl;
        std::cout << "\nTWAP:" << std::endl;
        std::cout << "  Time: " << std::fixed << std::setprecision(2) << twap_time << " ms" << std::endl;
        std::cout << "  Throughput: " << std::scientific << (num_iterations / twap_time) * 1000 << " gen/sec" << std::endl;
        
        std::cout << "\nVWAP:" << std::endl;
        std::cout << "  Time: " << std::fixed << std::setprecision(2) << vwap_time << " ms" << std::endl;
        std::cout << "  Throughput: " << std::scientific << (num_iterations / vwap_time) * 1000 << " gen/sec" << std::endl;
    }
    
    /**
     * Benchmark 5: Market simulator
     * 
     * Measures: How fast can we run a full backtest?
     * Expected: ~1000 backtests per second
     */
    void benchmark_market_simulator() {
        std::cout << "\n" << std::string(70, '=') << std::endl;
        std::cout << "BENCHMARK 5: Market Simulator" << std::endl;
        std::cout << std::string(70, '=') << std::endl;
        
        LiquidityModel liq(0.01, 1000, 0.0001);
        const int num_backtests = 1000;
        
        double time_ms = measure_ms([&]() {
            for (int b = 0; b < num_backtests; ++b) {
                MarketSimulator sim(100.0, liq);
                
                // Create orders
                std::vector<Order> orders;
                for (int i = 0; i < 10; ++i) {
                    orders.push_back(Order(i, OrderSide::Buy, OrderType::Limit, 100.0, 100));
                }
                
                // Run backtest
                sim.run_backtest(orders, 5, 0.01);
            }
        });
        
        double backtest_per_sec = (num_backtests / time_ms) * 1000;
        
        std::cout << "Backtests: " << num_backtests << std::endl;
        std::cout << "Time: " << std::fixed << std::setprecision(2) << time_ms << " ms" << std::endl;
        std::cout << "Throughput: " << std::scientific << backtest_per_sec << " backtests/sec" << std::endl;
        std::cout << "Per backtest: " << (time_ms / num_backtests) << " ms" << std::endl;
    }
    
    /**
     * Benchmark 6: End-to-end execution (full workflow)
     * 
     * Measures: Complete order -> match -> analyze pipeline
     */
    void benchmark_end_to_end() {
        std::cout << "\n" << std::string(70, '=') << std::endl;
        std::cout << "BENCHMARK 6: End-to-End Execution" << std::endl;
        std::cout << std::string(70, '=') << std::endl;
        
        const int num_runs = 100;
        
        double time_ms = measure_ms([&]() {
            for (int run = 0; run < num_runs; ++run) {
                // Create market and algorithm
                LiquidityModel liq(0.01, 1000, 0.0001);
                MarketSimulator sim(100.0, liq);
                TWAPAlgorithm twap;
                
                // Generate orders
                auto orders = twap.generate_orders(run, OrderSide::Buy, 10000, 100.0, 10);
                
                // Run backtest
                sim.run_backtest(orders, 10, 0.01);
                
                // Analyze trades
                auto trades = sim.get_engine().get_all_trades();
                double total_qty = 0;
                double total_cost = 0;
                for (const auto& t : trades) {
                    total_qty += t.qty;
                    total_cost += t.price * t.qty;
                }
                double avg_price = (total_qty > 0) ? (total_cost / total_qty) : 0;
                (void)avg_price;  // Use variable
            }
        });
        
        std::cout << "Full runs: " << num_runs << std::endl;
        std::cout << "Time: " << std::fixed << std::setprecision(2) << time_ms << " ms" << std::endl;
        std::cout << "Per run: " << (time_ms / num_runs) << " ms" << std::endl;
        std::cout << "Throughput: " << std::scientific << (num_runs / time_ms) * 1000 << " runs/sec" << std::endl;
    }
    
    /**
     * Run all benchmarks
     */
    void run_all() {
        std::cout << "\n";
        std::cout << "╔" << std::string(68, '=') << "╗" << std::endl;
        std::cout << "║" << std::string(68, ' ') << "║" << std::endl;
        std::cout << "║" << std::string(17, ' ') << "  PHASE 6: Performance Benchmarks" << std::string(18, ' ') << "║" << std::endl;
        std::cout << "║" << std::string(68, ' ') << "║" << std::endl;
        std::cout << "╚" << std::string(68, '=') << "╝" << std::endl;
        
        benchmark_order_book_insertion();
        benchmark_order_book_queries();
        benchmark_matching_engine();
        benchmark_algorithms();
        benchmark_market_simulator();
        benchmark_end_to_end();
        
        std::cout << "\n" << std::string(70, '=') << std::endl;
        std::cout << "✓ All benchmarks completed!" << std::endl;
        std::cout << std::string(70, '=') << std::endl;
    }
};

int main() {
    Benchmark bench;
    bench.run_all();
    return 0;
}