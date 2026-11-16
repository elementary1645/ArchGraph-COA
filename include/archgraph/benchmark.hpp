#pragma once
#include "dynagraph/algorithms/sssp.hpp"
#include <ostream>
#include <string>
namespace archgraph {
int benchmark(const dynagraph::CSRGraph& graph, dynagraph::VertexId source,
              const std::string& algorithm, dynagraph::Distance delta, int threads,
              unsigned repetitions, unsigned warmups, std::ostream& output, bool hardware_counters = false);
}
