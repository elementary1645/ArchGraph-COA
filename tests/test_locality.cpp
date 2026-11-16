#include "archgraph/experiments.hpp"
#include "test_support.hpp"
#include <algorithm>
#include <numeric>
using namespace archgraph;
using dynagraph::test::require;
int main() {
    return dynagraph::test::run("deterministic locality sequences and checksums", [] {
        for (const std::string pattern : {"sequential","strided","random","temporal"}) {
            for (const std::uint64_t n : {1U,2U,6U,257U}) {
                for (const std::uint64_t stride : {1U,2U,7U,1000U}) {
                    const auto sequence = access_sequence(pattern,n,stride,1234);
                    require(sequence == access_sequence(pattern,n,stride,1234), "Repeatable sequence");
                    auto sorted = sequence; std::sort(sorted.begin(),sorted.end());
                    for (std::size_t i = 0; i < n; ++i) { require(sorted[i] == i, "Exact permutation including noncoprime stride"); }
                    std::vector<std::uint64_t> data(static_cast<std::size_t>(n)); std::iota(data.begin(),data.end(),UINT64_MAX-3);
                    for (const std::uint64_t accesses : {0U,1U,13U,1000U}) {
                        std::uint64_t expected = 0;
                        for (std::uint64_t i = 0; i < accesses; ++i) { expected += data[sequence[static_cast<std::size_t>(i%n)]]; }
                        require(read_sequence(data,sequence,accesses) == expected, "Read checksum including overflow and partial cycles");
                    }
                }
            }
        }
        require(access_sequence("strided",6,2,0) == std::vector<std::uint32_t>({0,2,4,1,3,5}), "Strided golden");
        require(access_sequence("random",257,1,1) != access_sequence("random",257,1,2), "Seed changes order");
        dynagraph::test::require_throws<std::invalid_argument>([]{(void)access_sequence("other",8,1,0);}, "pattern");
        dynagraph::test::require_throws<std::invalid_argument>([]{(void)access_sequence("random",0,1,0);}, "invalid");
        dynagraph::test::require_throws<std::invalid_argument>([]{(void)access_sequence("strided",8,0,0);}, "invalid");
        dynagraph::test::require_throws<std::out_of_range>([]{(void)read_sequence({1,2},{2},1);}, "index");
        dynagraph::test::require_throws<std::invalid_argument>([]{(void)read_sequence({1,2},{},1);}, "Empty");
    });
}
