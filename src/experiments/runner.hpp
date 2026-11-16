#pragma once
#include "archgraph/experiments.hpp"
#include "archgraph/perf.hpp"
#include <algorithm>
#include <chrono>
#include <iomanip>
#include <memory>
#include <sstream>
#include <stdexcept>
namespace archgraph::experiment {
std::uint64_t read_sequence_kernel(const std::vector<std::uint64_t>& data, const std::vector<std::uint32_t>& sequence, std::uint64_t accesses);
struct Trial { std::int64_t wall_ns = 0; std::uint64_t checksum = 0; perf::Counters counters; };
using Trials = std::vector<Trial>;
template<class Run, class Verify>
Trials measure(const ExperimentOptions& options, Run run, Verify verify) {
    if (options.repetitions == 0 || options.repetitions > 10000 || options.warmups > 10000) {
        throw std::invalid_argument("repetitions must be [1,10000]; warmups [0,10000]");
    }
    for (unsigned i = 0; i < options.warmups; ++i) { (void)verify(run()); }
    Trials trials(options.repetitions);
    for (auto& trial : trials) {
        std::unique_ptr<perf::Session> counters;
        if (options.hardware_counters) { counters = std::make_unique<perf::Session>(perf::system_backend(),perf::EventSet::memory); counters->start(); }
        const auto begin = std::chrono::steady_clock::now();
        const auto result = run();
        const auto end = std::chrono::steady_clock::now();
        if (counters) { trial.counters = counters->stop(); }
        else { trial.counters = perf::unavailable("not_requested", "hardware counters were not requested"); }
        trial.wall_ns = std::chrono::duration_cast<std::chrono::nanoseconds>(end-begin).count();
        if (trial.wall_ns < 0) { throw std::runtime_error("Clock moved backwards"); }
        trial.checksum = verify(result); // Outside both windows; no completed JSON on mismatch.
    }
    return trials;
}
inline std::string trials_json(const Trials& trials) {
    std::vector<std::int64_t> times; times.reserve(trials.size());
    for (const auto& trial : trials) { times.push_back(trial.wall_ns); }
    std::sort(times.begin(),times.end()); const auto middle = times.size()/2;
    const double median = times.size()%2 == 0 ? static_cast<double>(times[middle-1])/2 + static_cast<double>(times[middle])/2 : static_cast<double>(times[middle]);
    std::string status = perf::overall_status(trials[0].counters);
    for (const auto& t : trials) { if (perf::overall_status(t.counters) != status) { status = "mixed"; break; } }
    std::ostringstream out; out << std::setprecision(17) << "{\"median_wall_ns\":" << median << ",\"counter_status\":" << perf::json_quote(status) << ",\"runs\":[";
    for (std::size_t i = 0; i < trials.size(); ++i) {
        if (i != 0) { out << ','; } const auto& t = trials[i];
        out << "{\"wall_ns\":" << t.wall_ns << ",\"checksum\":" << t.checksum
            << ",\"counters\":" << perf::counters_json(t.counters,perf::EventSet::memory)
            << ",\"derived\":" << perf::derived_json(t.counters,perf::EventSet::memory) << '}';
    }
    out << "]}"; return out.str();
}
inline auto checksum_verifier(std::uint64_t expected) {
    return [expected](std::uint64_t value) {
        if (value != expected) { throw std::runtime_error("Traversal checksum mismatch"); } return value;
    };
}
}
