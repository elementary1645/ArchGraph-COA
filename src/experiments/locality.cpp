#include "archgraph/experiments.hpp"
#include <numeric>
#include <stdexcept>
namespace archgraph {
namespace {
// SplitMix64 transition reused from upstream benchmarks/python/deterministic.py;
// source attribution/commit remain in docs/IMPORT_PROVENANCE.md.
struct SplitMix64 {
    std::uint64_t state;
    std::uint64_t next() {
        state += 0x9e3779b97f4a7c15ULL;
        auto z = state; z = (z ^ (z >> 30)) * 0xbf58476d1ce4e5b9ULL;
        z = (z ^ (z >> 27)) * 0x94d049bb133111ebULL;
        return z ^ (z >> 31);
    }
    std::uint64_t bounded(std::uint64_t bound) {
        const auto threshold = (0ULL-bound)%bound;
        for (;;) { const auto value = next(); if (value >= threshold) { return value%bound; } }
    }
};
}
std::vector<std::uint32_t> access_sequence(const std::string& pattern, std::uint64_t elements, std::uint64_t stride, std::uint64_t seed) {
    if (elements == 0 || elements > 33554432 || stride == 0) { throw std::invalid_argument("invalid sequence elements or stride"); }
    if (pattern != "sequential" && pattern != "strided" && pattern != "random" && pattern != "temporal") {
        throw std::invalid_argument("Unknown array pattern");
    }
    std::vector<std::uint32_t> sequence; sequence.reserve(static_cast<std::size_t>(elements));
    if (pattern == "strided") {
        for (std::uint64_t start = 0; start < elements && start < stride; ++start) {
            for (auto i = start; i < elements;) {
                sequence.push_back(static_cast<std::uint32_t>(i));
                if (elements-i <= stride) { break; } i += stride;
            }
        }
    } else {
        for (std::uint64_t i = 0; i < elements; ++i) { sequence.push_back(static_cast<std::uint32_t>(i)); }
        if (pattern == "random" || pattern == "temporal") {
            SplitMix64 random{seed};
            for (auto n = elements; n > 1; --n) { std::swap(sequence[static_cast<std::size_t>(n-1)],sequence[static_cast<std::size_t>(random.bounded(n))]); }
        }
    }
    return sequence;
}
namespace experiment {
std::uint64_t read_sequence_kernel(const std::vector<std::uint64_t>& data, const std::vector<std::uint32_t>& sequence, std::uint64_t accesses) {
    const volatile std::uint64_t* values = data.data();
    const volatile std::uint32_t* indices = sequence.data();
    std::uint64_t sum = 0; std::size_t pos = 0;
    for (std::uint64_t i = 0; i < accesses; ++i) {
        sum += values[indices[pos]];
        if (++pos == sequence.size()) { pos = 0; }
    }
    return sum;
}
}
std::uint64_t read_sequence(const std::vector<std::uint64_t>& data, const std::vector<std::uint32_t>& sequence, std::uint64_t accesses) {
    if (sequence.empty()) { throw std::invalid_argument("Empty access sequence"); }
    for (auto index : sequence) { if (index >= data.size()) { throw std::out_of_range("access sequence index"); } }
    return experiment::read_sequence_kernel(data,sequence,accesses);
}
}
