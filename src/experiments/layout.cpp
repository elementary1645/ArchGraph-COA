#include "archgraph/layout.hpp"
#include <fstream>
#include <functional>
#include <queue>
#include <sstream>
#include <stdexcept>
#ifdef __linux__
#include <unistd.h>
#endif
namespace archgraph {
AdjacencyGraph::AdjacencyGraph(const dynagraph::CSRGraph& graph)
    : rows_(static_cast<std::size_t>(graph.vertex_count())), edges_(graph.edge_count()) {
    for (std::uint64_t u = 0; u < graph.vertex_count(); ++u) {
        auto& row = rows_[static_cast<std::size_t>(u)];
        row.reserve(static_cast<std::size_t>(graph.degree(u)));
        for (const auto edge : graph.outgoing_edges(u)) { row.push_back({edge.destination, edge.weight}); }
    }
}
AdjacencyGraph AdjacencyGraph::from_edges(std::uint64_t vertices, std::vector<dynagraph::InputEdge> edges) {
    // Reuse all original validation, including rejection of duplicate directed edges.
    return AdjacencyGraph(dynagraph::CSRGraph::from_edges(vertices, std::move(edges)));
}
dynagraph::CSRGraph AdjacencyGraph::to_csr() const {
    std::vector<dynagraph::InputEdge> edges; edges.reserve(static_cast<std::size_t>(edges_));
    for (std::uint64_t u = 0; u < vertex_count(); ++u) {
        for (const auto edge : outgoing_edges(u)) {
            edges.push_back({static_cast<std::int64_t>(u), edge.destination, edge.weight});
        }
    }
    return dynagraph::CSRGraph::from_edges(vertex_count(), std::move(edges));
}
dynagraph::SSSPResult adjacency_dijkstra(const AdjacencyGraph& graph, dynagraph::VertexId source) {
    // Adapted from DynaGraph-HPC src/algorithms/dijkstra.cpp at the commit in
    // docs/IMPORT_PROVENANCE.md. Same lazy priority queue and relaxation semantics;
    // only the graph type/edge-range adapter differs. No instrumented work counts.
    using namespace dynagraph;
    if (source >= graph.vertex_count()) { throw std::out_of_range("source outside [0, V)"); }
    SSSPResult result{source, std::vector<Distance>(static_cast<std::size_t>(graph.vertex_count()), unreachable_distance)};
    using Entry = std::pair<Distance, VertexId>;
    std::priority_queue<Entry, std::vector<Entry>, std::greater<Entry>> queue;
    result.distances[source] = 0; queue.emplace(0, source);
    while (!queue.empty()) {
        const auto [distance, vertex] = queue.top(); queue.pop();
        if (distance != result.distances[vertex]) { continue; }
        for (const auto edge : graph.outgoing_edges(vertex)) {
            const Distance candidate = distance + edge.weight; // Same proven uint64 bound as baseline.
            if (candidate < result.distances[edge.destination]) {
                result.distances[edge.destination] = candidate;
                queue.emplace(candidate, edge.destination);
            }
        }
    }
    return result;
}
MemoryUsage memory_usage(const dynagraph::CSRGraph& graph) {
    MemoryUsage m;
    m.logical_payload_bytes = graph.edge_count() * (sizeof(dynagraph::VertexId) + sizeof(dynagraph::EdgeWeight));
    m.used_metadata_bytes = graph.offsets().size() * sizeof(dynagraph::EdgeOffset);
    m.capacity_storage_bytes = graph.offsets().capacity() * sizeof(dynagraph::EdgeOffset) +
        graph.destinations().capacity() * sizeof(dynagraph::VertexId) + graph.weights().capacity() * sizeof(dynagraph::EdgeWeight);
    m.container_object_bytes = sizeof(graph);
    m.allocation_blocks = (graph.offsets().capacity() != 0 ? 1U : 0U) +
        (graph.destinations().capacity() != 0 ? 1U : 0U) + (graph.weights().capacity() != 0 ? 1U : 0U);
    return m;
}
MemoryUsage memory_usage(const AdjacencyGraph& graph) {
    MemoryUsage m;
    m.logical_payload_bytes = graph.edge_count() * (sizeof(dynagraph::VertexId) + sizeof(dynagraph::EdgeWeight));
    m.used_metadata_bytes = graph.rows().size() * sizeof(std::vector<AdjacentEdge>);
    m.capacity_storage_bytes = graph.rows().capacity() * sizeof(std::vector<AdjacentEdge>);
    m.container_object_bytes = sizeof(graph);
    m.allocation_blocks = graph.rows().capacity() != 0 ? 1 : 0;
    for (const auto& row : graph.rows()) {
        m.capacity_storage_bytes += row.capacity() * sizeof(AdjacentEdge);
        m.allocation_blocks += row.capacity() != 0 ? 1U : 0U;
    }
    return m;
}
std::string memory_json(const MemoryUsage& m) {
    std::ostringstream out;
    out << "{\"logical_payload_bytes\":" << m.logical_payload_bytes << ",\"used_metadata_bytes\":" << m.used_metadata_bytes
        << ",\"capacity_storage_bytes\":" << m.capacity_storage_bytes << ",\"container_object_bytes\":" << m.container_object_bytes
        << ",\"container_overhead_estimate_bytes\":" << m.container_object_bytes + m.used_metadata_bytes
        << ",\"allocation_blocks\":" << m.allocation_blocks << ",\"allocator_overhead_bytes\":null"
        << ",\"accounted_total_bytes\":" << m.capacity_storage_bytes + m.container_object_bytes
        << ",\"physical_memory_bytes\":null}";
    return out.str();
}
std::string process_memory_json() {
    std::ostringstream out; out << "{\"rss_bytes\":";
#ifdef __linux__
    std::ifstream input("/proc/self/statm");
    std::uint64_t total = 0, resident = 0;
    const long page_size = sysconf(_SC_PAGESIZE);
    if (input >> total >> resident && page_size > 0 && resident <= UINT64_MAX / static_cast<std::uint64_t>(page_size)) {
        out << resident * static_cast<std::uint64_t>(page_size);
    } else { out << "null"; }
#else
    out << "null";
#endif
    out << ",\"source\":\"/proc/self/statm * sysconf(_SC_PAGESIZE); whole-process snapshot, not per-layout allocation\"}";
    return out.str();
}
std::uint64_t traverse(const dynagraph::CSRGraph& graph, unsigned passes) {
    // Volatile reads enforce consumption on every trial, at the cost of scalar loads.
    const volatile auto* offsets = graph.offsets().data();
    const volatile auto* destinations = graph.destinations().data();
    const volatile auto* weights = graph.weights().data();
    std::uint64_t checksum = 0;
    for (unsigned pass = 0; pass < passes; ++pass) {
        for (std::uint64_t u = 0; u < graph.vertex_count(); ++u) {
            const auto end = offsets[u + 1];
            for (auto e = offsets[u]; e < end; ++e) {
                checksum += (static_cast<std::uint64_t>(destinations[e]) << 32) | weights[e];
            }
        }
    }
    return checksum;
}
std::uint64_t traverse(const AdjacencyGraph& graph, unsigned passes) {
    std::uint64_t checksum = 0;
    for (unsigned pass = 0; pass < passes; ++pass) {
        for (const auto& row : graph.rows()) {
            for (const volatile auto& edge : row) {
                checksum += (static_cast<std::uint64_t>(edge.destination) << 32) | edge.weight;
            }
        }
    }
    return checksum;
}
}
