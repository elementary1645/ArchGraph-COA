#include "archgraph/benchmark.hpp"
#include "archgraph/analysis.hpp"
#include "dynagraph/algorithms/delta_stepping.hpp"
#include <chrono>
#include <stdexcept>
#include <vector>
namespace archgraph {
int benchmark(const dynagraph::CSRGraph& graph, dynagraph::VertexId source,
              const std::string& algorithm, dynagraph::Distance delta, int threads,
              unsigned repetitions, unsigned warmups, std::ostream& output) {
    if ((algorithm != "dijkstra" && algorithm != "delta-stepping") || repetitions == 0 ||
        repetitions > 10000 || warmups > 10000) { throw std::invalid_argument("Invalid benchmark configuration"); }
            // Adapted from upstream src/benchmark/timing.cpp: monotonic wall clock,
            // with allocation of sample storage and verification outside brackets.
            const auto reference = dynagraph::dijkstra(graph, source);
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
            std::vector<std::int64_t> samples(repetitions);
            for (unsigned i = 0; i < repetitions; ++i) {
                const auto start = std::chrono::steady_clock::now();
                const auto result = run();
                const auto stop = std::chrono::steady_clock::now();
                verify(result);
                samples[i] = std::chrono::duration_cast<std::chrono::nanoseconds>(stop - start).count();
                if (samples[i] < 0) { throw std::runtime_error("Clock moved backwards"); }
            }
            output << "{\"schema_version\":1,\"algorithm\":\"" << algorithm
                      << "\",\"source\":" << source << ",\"vertices\":" << graph.vertex_count()
                      << ",\"edges\":" << graph.edge_count() << ",\"delta\":" << delta
                      << ",\"requested_threads\":" << threads << ",\"actual_threads\":null"
                      << ",\"warmups\":" << warmups << ",\"repetitions\":" << repetitions
                      << ",\"verified\":true,\"unit\":\"wall_ns\",\"samples\":[";
            for (std::size_t i = 0; i < samples.size(); ++i) {
                if (i != 0) { output << ','; }
                output << samples[i];
            }
            output << "],\"metadata\":" << archgraph::cpu_metadata() << "}\n";
            return output ? 0 : 2;
}
}
