#pragma once
#include "dynagraph/algorithms/sssp.hpp"
#include <string>
namespace archgraph {
struct AdjacentEdge { dynagraph::VertexId destination; dynagraph::EdgeWeight weight; };
class AdjacencyGraph {
public:
    explicit AdjacencyGraph(const dynagraph::CSRGraph& graph);
    static AdjacencyGraph from_edges(std::uint64_t vertices, std::vector<dynagraph::InputEdge> edges);
    dynagraph::CSRGraph to_csr() const;
    std::uint64_t vertex_count() const { return rows_.size(); }
    std::uint64_t edge_count() const { return edges_; }
    const std::vector<AdjacentEdge>& outgoing_edges(std::uint64_t vertex) const { return rows_.at(static_cast<std::size_t>(vertex)); }
    const std::vector<std::vector<AdjacentEdge>>& rows() const { return rows_; }
private:
    std::vector<std::vector<AdjacentEdge>> rows_;
    std::uint64_t edges_ = 0;
};
// Isolated adapter of upstream lazy-heap Dijkstra; imported baseline stays untouched.
dynagraph::SSSPResult adjacency_dijkstra(const AdjacencyGraph& graph, dynagraph::VertexId source);
struct MemoryUsage {
    std::uint64_t logical_payload_bytes = 0, used_metadata_bytes = 0;
    std::uint64_t capacity_storage_bytes = 0, container_object_bytes = 0, allocation_blocks = 0;
};
MemoryUsage memory_usage(const dynagraph::CSRGraph& graph);
MemoryUsage memory_usage(const AdjacencyGraph& graph);
std::string memory_json(const MemoryUsage& usage);
std::string process_memory_json();
std::uint64_t traverse(const dynagraph::CSRGraph& graph, unsigned passes);
std::uint64_t traverse(const AdjacencyGraph& graph, unsigned passes);
}
