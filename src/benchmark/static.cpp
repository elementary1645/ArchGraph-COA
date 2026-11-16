#include "archgraph/benchmark.hpp"
#include "archgraph/analysis.hpp"
#include "archgraph/identity.hpp"
#include "archgraph/perf.hpp"
#include "dynagraph/algorithms/delta_stepping.hpp"
#include <algorithm>
#include <chrono>
#include <iomanip>
#include <memory>
#include <sstream>
#include <stdexcept>
#include <vector>
namespace archgraph {
// Noncryptographic identity of loaded CSR: uint64 little-endian counts followed
// by offsets, destinations and weights, each promoted to uint64 little-endian.
std::string graph_identity(const dynagraph::CSRGraph& graph) {
    std::uint64_t hash = 14695981039346656037ULL;
    const auto append = [&](std::uint64_t value) {
        for (unsigned byte = 0; byte < 8; ++byte) {
            hash ^= value & 255U; hash *= 1099511628211ULL; value >>= 8;
        }
    };
    append(graph.vertex_count()); append(graph.edge_count());
    for (auto value : graph.offsets()) { append(value); }
    for (auto value : graph.destinations()) { append(value); }
    for (auto value : graph.weights()) { append(value); }
    std::ostringstream out; out << std::hex << std::setw(16) << std::setfill('0') << hash;
    return out.str();
}
int benchmark(const dynagraph::CSRGraph& graph, dynagraph::VertexId source,
              const std::string& algorithm, dynagraph::Distance delta, int threads,
              unsigned repetitions, unsigned warmups, std::ostream& output, bool hardware_counters) {
    if ((algorithm != "dijkstra" && algorithm != "delta-stepping") || repetitions == 0 ||
        repetitions > 10000 || warmups > 10000) { throw std::invalid_argument("Invalid benchmark configuration"); }
    // Imported algorithm boundaries and correctness baseline remain unchanged.
    const auto reference = dynagraph::dijkstra(graph, source);
    const auto identity = graph_identity(graph);
    const auto run = [&]() {
        return algorithm == "dijkstra" ? dynagraph::dijkstra(graph, source) :
            dynagraph::delta_stepping(graph, source, {delta, threads});
    };
    const auto verify = [&](const dynagraph::SSSPResult& result) {
        if (result.source != reference.source || result.distances != reference.distances) {
            throw std::runtime_error("Benchmark correctness mismatch");
        }
    };
    for (unsigned i = 0; i < warmups; ++i) { verify(run()); }
    const bool supported_scope = hardware_counters && algorithm == "dijkstra";
    std::vector<std::int64_t> samples(repetitions);
    std::vector<perf::Counters> readings(repetitions);
    for (unsigned i = 0; i < repetitions; ++i) {
        // Fresh descriptors avoid cumulative time_enabled/time_running across resets.
        std::unique_ptr<perf::Session> counters;
        if (supported_scope) { counters = std::make_unique<perf::Session>(); counters->start(); }
        const auto start = std::chrono::steady_clock::now();
        const auto result = run();
        const auto stop = std::chrono::steady_clock::now();
        if (counters) { readings[i] = counters->stop(); }
        else {
            readings[i] = perf::unavailable(hardware_counters ? "unsupported_scope" : "not_requested",
                hardware_counters ? "OpenMP worker aggregation is not implemented; no caller-only proxy is collected" : "hardware counters were not requested");
        }
        verify(result);
        samples[i] = std::chrono::duration_cast<std::chrono::nanoseconds>(stop - start).count();
        if (samples[i] < 0) { throw std::runtime_error("Clock moved backwards"); }
    }
    auto ordered = samples;
    std::sort(ordered.begin(), ordered.end());
    const auto middle = ordered.size() / 2;
    const double median = ordered.size() % 2 == 0 ?
        static_cast<double>(ordered[middle - 1]) / 2 + static_cast<double>(ordered[middle]) / 2 :
        static_cast<double>(ordered[middle]);
    std::string counter_status = perf::overall_status(readings[0]);
    for (const auto& reading : readings) {
        if (perf::overall_status(reading) != counter_status) { counter_status = "mixed"; break; }
    }
    output << std::setprecision(17) << "{\"schema_version\":1,\"algorithm\":\"" << algorithm
           << "\",\"status\":\"completed\",\"source\":" << source << ",\"vertices\":" << graph.vertex_count()
           << ",\"edges\":" << graph.edge_count() << ",\"delta\":" << delta
           << ",\"requested_threads\":" << threads << ",\"actual_threads\":null"
           << ",\"input_identity\":{\"method\":\"fnv1a64-csr-le-u64-v1\",\"value\":" << perf::json_quote(identity) << '}'
           << ",\"warmups\":" << warmups << ",\"repetitions\":" << repetitions
           << ",\"verified\":true,\"unit\":\"wall_ns\",\"median_wall_ns\":" << median << ",\"samples\":[";
    for (std::size_t i = 0; i < samples.size(); ++i) {
        if (i != 0) { output << ','; } output << samples[i];
    }
    output << "],\"hardware_counters_requested\":" << (hardware_counters ? "true" : "false")
           << ",\"counter_status\":" << perf::json_quote(counter_status)
           << ",\"measurement_scope\":{\"hardware\":\"calling_thread_user_space\",\"inherit\":false,\"kernel\":false,\"hypervisor\":false,\"thread_aggregation\":false,\"groups\":[[\"cpu_cycles\",\"instructions\"],[\"cache_references\",\"cache_misses\"],[\"branch_instructions\",\"branch_misses\"]]}"
           << ",\"warnings\":[";
    if (hardware_counters) {
        output << perf::json_quote(supported_scope ?
            "Counter windows include clock/control boundary overhead; multiplexed values are scaled estimates; inspect every per-event status. Shared/virtualized CPUs do not establish controlled performance." :
            "Hardware counters are unsupported for delta-stepping; wall-clock and correctness checks still run.");
    }
    output << "],\"runs\":[";
    for (std::size_t i = 0; i < samples.size(); ++i) {
        if (i != 0) { output << ','; }
        output << "{\"index\":" << i << ",\"wall_ns\":" << samples[i]
               << ",\"counter_status\":" << perf::json_quote(perf::overall_status(readings[i]))
               << ",\"counters\":" << perf::counters_json(readings[i])
               << ",\"derived\":" << perf::derived_json(readings[i]) << '}';
    }
    output << "],\"metadata\":" << cpu_metadata() << "}\n";
    return output ? 0 : 2;
}
}
