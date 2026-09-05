#ifndef EXECUTOR_MARKET_DATA_H
#define EXECUTOR_MARKET_DATA_H

#include "types.h"
#include <cstdint>
#include <string>
#include <vector>

/**
 * Canonical market view used by the execution session.
 *
 * Every source (synthetic, real-time adapter, historical CSV) produces this.
 * The matching engine never sees Yahoo JSON or CSV columns.
 *
 * Depth: bids/asks are best-first. Empty vectors mean "top-of-book only";
 * the session will then post a single level from bid/ask + sizes.
 */
struct MarketState {
    double last_price = 0.0;
    double mid_price = 0.0;
    double bid = 0.0;
    double ask = 0.0;
    uint64_t bid_volume = 0;
    uint64_t ask_volume = 0;
    uint64_t volume = 0;       // cumulative volume if the source provides it
    uint64_t bar_volume = 0;   // volume during this event/bar (for market VWAP)
    uint64_t timestamp_ms = 0;
    std::vector<BookLevel> bids;
    std::vector<BookLevel> asks;
};

using MarketSnapshot = MarketState;

/**
 * Pull-style feed. next() must be chronological: no future information.
 */
class MarketDataSource {
public:
    virtual ~MarketDataSource() = default;
    virtual bool next(MarketState& out) = 0;
    virtual void reset() = 0;
    virtual std::string name() const = 0;
};

/**
 * In-memory sequence. Used by tests and by Python after it has adapted
 * an external API into MarketState objects.
 */
class VectorMarketSource : public MarketDataSource {
public:
    explicit VectorMarketSource(std::vector<MarketState> states);
    bool next(MarketState& out) override;
    void reset() override;
    std::string name() const override { return "vector"; }

private:
    std::vector<MarketState> states_;
    size_t index_ = 0;
};

class RealtimeMarketSource : public MarketDataSource {
public:
    bool publish(MarketState state);
    bool next(MarketState& out) override;
    void reset() override;
    std::string name() const override { return "realtime"; }

private:
    std::vector<MarketState> states_;
    size_t index_ = 0;
    uint64_t last_timestamp_ms_ = 0;
};

/**
 * Historical / recorded real-market replay.
 *
 * CSV columns (header required):
 *   timestamp_ms,last,bid,ask,bid_size,ask_size,volume
 * Optional:
 *   bid_depth,ask_depth   format price:qty|price:qty  (best first)
 *
 * If depth columns are absent, only top-of-book is available.
 */
class CsvMarketSource : public MarketDataSource {
public:
    explicit CsvMarketSource(std::string path);
    bool next(MarketState& out) override;
    void reset() override;
    std::string name() const override { return "csv"; }
    bool ok() const { return loaded_; }

private:
    std::string path_;
    std::vector<MarketState> states_;
    size_t index_ = 0;
    bool loaded_ = false;

    void load();
};

void normalize_market_state(MarketState& state);

#endif
