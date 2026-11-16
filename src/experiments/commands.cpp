#include "archgraph/experiments.hpp"
#include "archgraph/analysis.hpp"
#include "archgraph/cache.hpp"
#include "archgraph/identity.hpp"
#include "archgraph/layout.hpp"
#include "dynagraph/graph/edge_list_io.hpp"
#include "runner.hpp"
#include <iomanip>
#include <numeric>
#include <sstream>
namespace archgraph {
namespace {
void validate_bytes(std::uint64_t bytes) {
    if (bytes < 8 || bytes > 268435456 || bytes%8 != 0) { throw std::invalid_argument("size/working-set must be 8-byte aligned in [8,268435456]"); }
}
std::string array_experiment(const ExperimentOptions& o) {
    validate_bytes(o.size);
    const auto active = o.pattern == "temporal" ? o.working_set : o.size;
    validate_bytes(active);
    if (active > o.size) { throw std::invalid_argument("working-set exceeds allocated size"); }
    const auto elements = active/8;
    const auto accesses = o.accesses == 0 ? (o.pattern == "temporal" ? std::max<std::uint64_t>(elements,1048576) : elements) : o.accesses;
    if (accesses > 100000000 || accesses == 0) { throw std::invalid_argument("accesses must be [1,100000000]"); }
    std::vector<std::uint64_t> data(static_cast<std::size_t>(o.size/8));
    for (std::size_t i = 0; i < data.size(); ++i) { data[i] = (static_cast<std::uint64_t>(i)*0x9e3779b97f4a7c15ULL) ^ o.seed; }
    const auto sequence = access_sequence(o.pattern,elements,o.stride,o.seed);
    std::uint64_t cycle_sum = 0, tail_sum = 0, fingerprint = 14695981039346656037ULL;
    for (std::size_t i = 0; i < sequence.size(); ++i) {
        const auto index = sequence[i]; cycle_sum += data[index];
        if (i < accesses%elements) { tail_sum += data[index]; }
        std::uint64_t value = index;
        for (unsigned b = 0; b < 8; ++b) { fingerprint ^= value & 255U; fingerprint *= 1099511628211ULL; value >>= 8; }
    }
    const auto expected = cycle_sum * (accesses/elements) + tail_sum;
    const auto trials = experiment::measure(o,[&]{return experiment::read_sequence_kernel(data,sequence,accesses);},experiment::checksum_verifier(expected));
    std::ostringstream out;
    out << "{\"pattern\":" << perf::json_quote(o.pattern) << ",\"allocated_data_bytes\":" << o.size
        << ",\"active_data_bytes\":" << active << ",\"sequence_payload_bytes\":" << sequence.size()*sizeof(std::uint32_t)
        << ",\"capacity_storage_bytes\":" << data.capacity()*sizeof(std::uint64_t)+sequence.capacity()*sizeof(std::uint32_t)
        << ",\"distinct_data_elements\":" << std::min(accesses,elements)
        << ",\"data_reads\":" << accesses << ",\"index_reads\":" << accesses
        << ",\"stride_elements\":" << o.stride << ",\"seed\":" << o.seed
        << ",\"sequence_fingerprint_u64\":" << fingerprint << ",\"expected_checksum\":" << expected
        << ",\"read_write_pattern\":\"volatile scalar index and uint64 data reads; no data writes in timing\""
        << ",\"timing\":" << experiment::trials_json(trials) << '}';
    return out.str();
}
std::uint64_t distance_checksum(const std::vector<dynagraph::Distance>& distances) {
    std::uint64_t sum = 0;
    for (auto value : distances) { sum = sum * 1099511628211ULL + value; } return sum;
}
std::uint64_t edge_checksum(const dynagraph::CSRGraph& graph, unsigned passes) {
    std::uint64_t expected = 0;
    for (std::uint64_t u = 0; u < graph.vertex_count(); ++u) {
        for (const auto edge : graph.outgoing_edges(u)) { expected += (static_cast<std::uint64_t>(edge.destination)<<32) | edge.weight; }
    }
    return expected * passes;
}
}
int experiment_command(const std::string& command, const ExperimentOptions& options, std::ostream& output) {
    if (options.repetitions == 0 || options.repetitions > 10000 || options.warmups > 10000 || options.passes == 0 || options.passes > 10000) {
        throw std::invalid_argument("invalid repetitions, warmups or passes");
    }
    const auto caches = discover_caches(options.cache_root);
    std::ostringstream result;
    if (command == "cache-study") {
        const auto plan = cache_plan(caches,options.sizes,options.maximum);
        auto o = options; o.pattern = "random";
        const auto largest = plan.sizes.back()/8;
        if (o.accesses == 0) { o.accesses = largest; }
        if (o.accesses < largest) { throw std::invalid_argument("cache-study accesses must cover the largest data working set at least once"); }
        result << "\"plan_mode\":" << perf::json_quote(plan.mode) << ",\"omitted_capacity_targets\":" << plan.omitted_targets
               << ",\"maximum_data_bytes\":" << o.maximum << ",\"experiments\":[";
        bool first = true;
        for (auto size : plan.sizes) {
            if (!first) { result << ','; } first = false; o.size = size;
            result << array_experiment(o);
        }
        result << ']';
    } else if (command == "locality" && options.pattern != "csr" && options.pattern != "adjacency") {
        result << "\"experiment\":" << array_experiment(options);
    } else {
        if (options.input.empty()) { throw std::invalid_argument("--input is required for graph experiments"); }
        const auto graph = dynagraph::load_edge_list_file(options.input);
        const AdjacencyGraph adjacency(graph);
        result << "\"input_identity\":{\"method\":\"fnv1a64-csr-le-u64-v1\",\"value\":" << perf::json_quote(graph_identity(graph)) << '}'
               << ",\"vertices\":" << graph.vertex_count() << ",\"edges\":" << graph.edge_count()
               << ",\"layouts\":{\"csr\":" << memory_json(memory_usage(graph)) << ",\"adjacency\":" << memory_json(memory_usage(adjacency)) << '}'
               << ",\"process_memory\":" << process_memory_json();
        if (command == "compare-layouts") {
            const auto reference = dynagraph::dijkstra(graph,options.source);
            const auto verify = [&](const dynagraph::SSSPResult& value) {
                if (value.source != reference.source || value.distances != reference.distances) { throw std::runtime_error("Layout SSSP mismatch"); }
                return distance_checksum(value.distances);
            };
            const auto csr_trials = experiment::measure(options,[&]{return dynagraph::dijkstra(graph,options.source);},verify);
            const auto adjacency_trials = experiment::measure(options,[&]{return adjacency_dijkstra(adjacency,options.source);},verify);
            result << ",\"source\":" << options.source << ",\"outputs_identical\":true,\"order\":\"csr_then_adjacency\""
                   << ",\"csr_dijkstra\":" << experiment::trials_json(csr_trials)
                   << ",\"adjacency_dijkstra\":" << experiment::trials_json(adjacency_trials);
        } else if (command == "locality") {
            const auto expected = edge_checksum(graph,options.passes);
            const auto trials = experiment::measure(options,[&]{return options.pattern == "csr" ? traverse(graph,options.passes) : traverse(adjacency,options.passes);},experiment::checksum_verifier(expected));
            if (graph.edge_count() > UINT64_MAX/options.passes) { throw std::overflow_error("edge access count overflow"); }
            result << ",\"pattern\":" << perf::json_quote(options.pattern) << ",\"passes\":" << options.passes
                   << ",\"edge_visits\":" << graph.edge_count()*options.passes << ",\"expected_checksum\":" << expected
                   << ",\"timing\":" << experiment::trials_json(trials);
        } else if (command != "memory") { throw std::invalid_argument("Unknown experiment command"); }
    }
    // Commit a complete JSON record only after all experiments verify successfully.
    output << "{\"schema\":\"archgraph-memory-experiments\",\"schema_version\":1,\"command\":" << perf::json_quote(command)
           << ",\"status\":\"completed\",\"verified\":true,\"repetitions\":" << options.repetitions << ",\"warmups\":" << options.warmups
           << ",\"hardware_counters_requested\":" << (options.hardware_counters ? "true" : "false")
           << ",\"measurement_scope\":\"calling_thread_user_space_no_inheritance; PMU windows include clock/control overhead\""
           << ",\"metadata\":" << cpu_metadata() << ",\"cache_info\":" << cache_json(caches)
           << ",\"environment_diagnostic\":" << perf::diagnostics()
           << ",\"warnings\":[\"Elapsed time alone does not establish cache hits/misses or a cache-level transition.\",\"Access sequence storage, TLB, prefetching, scalar volatile loads, scheduling and shared caches affect interpretation.\"]"
           << ',' << result.str() << "}\n";
    return output ? 0 : 2;
}
}
