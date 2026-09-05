#include "market_data.h"

#include <algorithm>
#include <fstream>
#include <sstream>
#include <unordered_map>

namespace {

std::vector<std::string> split_csv_line(const std::string& line) {
    std::vector<std::string> fields;
    std::stringstream stream(line);
    std::string field;
    while (std::getline(stream, field, ',')) {
        fields.push_back(field);
    }
    return fields;
}

std::vector<BookLevel> parse_depth(const std::string& value) {
    std::vector<BookLevel> levels;
    std::stringstream stream(value);
    std::string item;
    while (std::getline(stream, item, '|')) {
        const auto separator = item.find(':');
        if (separator == std::string::npos) {
            continue;
        }
        try {
            const double price = std::stod(item.substr(0, separator));
            const auto quantity = std::stoull(item.substr(separator + 1));
            if (price > 0.0 && quantity > 0) {
                levels.push_back({price, quantity});
            }
        } catch (const std::exception&) {
            // Ignore malformed depth entries while preserving the row.
        }
    }
    return levels;
}

} // namespace

VectorMarketSource::VectorMarketSource(std::vector<MarketState> states)
    : states_(std::move(states)) {
    for (auto& state : states_) {
        normalize_market_state(state);
    }
}

bool VectorMarketSource::next(MarketState& out) {
    if (index_ >= states_.size()) {
        return false;
    }
    out = states_[index_++];
    return true;
}

void VectorMarketSource::reset() {
    index_ = 0;
}

bool RealtimeMarketSource::publish(MarketState state) {
    if (!states_.empty() && state.timestamp_ms < last_timestamp_ms_) {
        return false;
    }
    normalize_market_state(state);
    last_timestamp_ms_ = state.timestamp_ms;
    states_.push_back(std::move(state));
    return true;
}

bool RealtimeMarketSource::next(MarketState& out) {
    if (index_ >= states_.size()) {
        return false;
    }
    out = states_[index_++];
    return true;
}

void RealtimeMarketSource::reset() {
    index_ = 0;
}

CsvMarketSource::CsvMarketSource(std::string path)
    : path_(std::move(path)) {
    load();
}

void CsvMarketSource::load() {
    std::ifstream input(path_);
    if (!input) {
        return;
    }

    std::string line;
    if (!std::getline(input, line)) {
        return;
    }

    const auto headers = split_csv_line(line);
    const std::vector<std::string> required = {
        "timestamp_ms", "last", "bid", "ask", "bid_size", "ask_size", "volume"
    };
    std::unordered_map<std::string, size_t> positions;
    for (size_t i = 0; i < headers.size(); ++i) {
        positions[headers[i]] = i;
    }
    for (const auto& header : required) {
        if (positions.find(header) == positions.end()) {
            return;
        }
    }

    while (std::getline(input, line)) {
        if (line.empty()) {
            continue;
        }
        const auto fields = split_csv_line(line);
        auto field = [&fields, &positions](const std::string& key) -> std::string {
            const auto it = positions.find(key);
            return it == positions.end() || it->second >= fields.size()
                ? std::string{}
                : fields[it->second];
        };

        try {
            MarketState state;
            state.timestamp_ms = std::stoull(field("timestamp_ms"));
            state.last_price = std::stod(field("last"));
            state.bid = std::stod(field("bid"));
            state.ask = std::stod(field("ask"));
            state.bid_volume = std::stoull(field("bid_size"));
            state.ask_volume = std::stoull(field("ask_size"));
            state.volume = std::stoull(field("volume"));
            if (positions.find("bar_volume") != positions.end()) {
                state.bar_volume = std::stoull(field("bar_volume"));
            }
            if (positions.find("bid_depth") != positions.end()) {
                state.bids = parse_depth(field("bid_depth"));
            }
            if (positions.find("ask_depth") != positions.end()) {
                state.asks = parse_depth(field("ask_depth"));
            }
            normalize_market_state(state);
            states_.push_back(std::move(state));
        } catch (const std::exception&) {
            states_.clear();
            return;
        }
    }
    std::stable_sort(states_.begin(), states_.end(),
                     [](const MarketState& left, const MarketState& right) {
                         return left.timestamp_ms < right.timestamp_ms;
                     });
    loaded_ = true;
}

bool CsvMarketSource::next(MarketState& out) {
    if (index_ >= states_.size()) {
        return false;
    }
    out = states_[index_++];
    return true;
}

void CsvMarketSource::reset() {
    index_ = 0;
}

void normalize_market_state(MarketState& state) {
    if (state.mid_price <= 0.0 && state.bid > 0.0 && state.ask > 0.0) {
        state.mid_price = (state.bid + state.ask) / 2.0;
    }
    if (state.last_price <= 0.0) {
        state.last_price = state.mid_price;
    }
    if (state.bids.empty() && state.bid > 0.0 && state.bid_volume > 0) {
        state.bids.push_back({state.bid, state.bid_volume});
    }
    if (state.asks.empty() && state.ask > 0.0 && state.ask_volume > 0) {
        state.asks.push_back({state.ask, state.ask_volume});
    }
    if (!state.bids.empty()) {
        state.bid = state.bids.front().price;
        state.bid_volume = state.bids.front().qty;
    }
    if (!state.asks.empty()) {
        state.ask = state.asks.front().price;
        state.ask_volume = state.asks.front().qty;
    }
    if (state.mid_price <= 0.0 && state.last_price > 0.0) {
        state.mid_price = state.last_price;
    }
}