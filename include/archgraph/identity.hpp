#pragma once
#include "dynagraph/graph/csr_graph.hpp"
#include <string>
namespace archgraph {
// Phase 2 fingerprint, now shared by layout experiments and the original benchmark.
std::string graph_identity(const dynagraph::CSRGraph& graph);
}
