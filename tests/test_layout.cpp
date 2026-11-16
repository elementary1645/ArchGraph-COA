#include "archgraph/layout.hpp"
#include "sssp_test_support.hpp"
#include "test_support.hpp"
#include <random>
using namespace archgraph;
using namespace dynagraph;
using dynagraph::test::require;
void check(std::uint64_t n, const std::vector<InputEdge>& edges) {
    const auto csr = CSRGraph::from_edges(n,edges);
    const AdjacencyGraph adjacency(csr);
    const auto restored = adjacency.to_csr();
    require(restored.offsets() == csr.offsets() && restored.destinations() == csr.destinations() &&
        restored.weights() == csr.weights(), "Exact canonical round trip");
    require(adjacency.vertex_count() == n && adjacency.edge_count() == edges.size(), "Counts preserved");
    for (VertexId source = 0; source < n; ++source) {
        const auto expected = dynagraph::test::bellman_ford(static_cast<std::size_t>(n),edges,source);
        require(adjacency_dijkstra(adjacency,source).distances == expected, "Adapter independent oracle");
        require(dijkstra(csr,source).distances == expected, "Original baseline oracle");
    }
    for (unsigned passes : {1U,3U}) {
        std::uint64_t expected = 0;
        for (const auto edge : edges) { expected += (static_cast<std::uint64_t>(edge.destination)<<32) | static_cast<std::uint64_t>(edge.weight); }
        require(traverse(csr,passes) == expected*passes && traverse(adjacency,passes) == expected*passes, "Equal traversal checksum");
    }
    const auto a = memory_usage(adjacency), c = memory_usage(csr);
    require(a.logical_payload_bytes == edges.size()*8 && a.logical_payload_bytes == c.logical_payload_bytes, "Equal logical edge payload");
    require(c.used_metadata_bytes == (n+1)*sizeof(EdgeOffset), "CSR metadata");
    require(a.used_metadata_bytes == n*sizeof(std::vector<AdjacentEdge>), "Adjacency metadata");
    std::uint64_t adjacency_capacity = adjacency.rows().capacity()*sizeof(std::vector<AdjacentEdge>);
    std::uint64_t blocks = adjacency.rows().capacity() == 0 ? 0 : 1;
    for (const auto& row : adjacency.rows()) { adjacency_capacity += row.capacity()*sizeof(AdjacentEdge); blocks += row.capacity() == 0 ? 0U : 1U; }
    require(a.capacity_storage_bytes == adjacency_capacity && a.allocation_blocks == blocks, "Actual vector capacity and allocation blocks");
    require(c.capacity_storage_bytes == csr.offsets().capacity()*sizeof(EdgeOffset) + csr.destinations().capacity()*sizeof(VertexId) + csr.weights().capacity()*sizeof(EdgeWeight), "CSR capacity accounting");
    require(a.capacity_storage_bytes >= a.logical_payload_bytes + a.used_metadata_bytes, "Capacity covers used storage");
    require(memory_json(a).find("\"allocator_overhead_bytes\":null") != std::string::npos, "Unknown allocator overhead explicit");
}
int main() {
    return dynagraph::test::run("layout semantics, oracle and memory accounting", [] {
        check(0,{}); check(4,{});
        check(5,{{0,0,0},{0,1,0},{1,2,4294967295LL},{2,2,4},{3,4,2}});
        dynagraph::test::require_throws<std::invalid_argument>([]{(void)AdjacencyGraph::from_edges(2,{{0,1,2},{0,1,3}});}, "duplicate");
        dynagraph::test::require_throws<std::invalid_argument>([]{(void)AdjacencyGraph::from_edges(2,{{0,1,2},{0,1,2}});}, "duplicate");
        dynagraph::test::require_throws<std::out_of_range>([]{const AdjacencyGraph g(CSRGraph{}); (void)adjacency_dijkstra(g,0);}, "source");
        std::mt19937 random(3017);
        for (unsigned trial = 0; trial < 30; ++trial) {
            const unsigned n = 1 + static_cast<unsigned>(random()%12); std::vector<InputEdge> edges;
            for (unsigned u = 0; u < n; ++u) { for (unsigned v = 0; v < n; ++v) {
                if (random()%4 == 0) { edges.push_back({u,v,static_cast<std::int64_t>(random()%32)}); }
            } }
            check(n,edges);
        }
    });
}
