#pragma once
#include <cstdint>
#include <ostream>
#include <string>
#include <vector>
namespace archgraph {
struct ExperimentOptions {
    unsigned repetitions = 5, warmups = 1, passes = 1;
    std::uint64_t size = 1048576, working_set = 4096, stride = 16, seed = 1, accesses = 0, maximum = 67108864;
    bool hardware_counters = false;
    std::string input, pattern = "sequential", cache_root;
    std::uint32_t source = 0;
    std::vector<std::uint64_t> sizes;
};
// Deterministic SplitMix64 Fisher-Yates permutation; strided covers each index once.
std::vector<std::uint32_t> access_sequence(const std::string& pattern, std::uint64_t elements, std::uint64_t stride, std::uint64_t seed);
std::uint64_t read_sequence(const std::vector<std::uint64_t>& data, const std::vector<std::uint32_t>& sequence, std::uint64_t accesses);
int experiment_command(const std::string& command, const ExperimentOptions& options, std::ostream& out);
int experiment_cli(int argc, char* argv[], std::ostream& out);
std::string experiment_help();
}
