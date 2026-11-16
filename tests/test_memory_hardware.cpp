#include "archgraph/perf.hpp"
#include <iostream>
int main() {
    using namespace archgraph::perf;
    Session session(system_backend(),EventSet::memory); session.start();
    volatile std::uint64_t data[1024]{};
    std::uint64_t checksum = 0;
    for (unsigned i = 0; i < 1000000; ++i) { checksum += data[i%1024]; }
    const auto counts = session.stop();
    std::cout << counters_json(counts,EventSet::memory) << '\n';
    bool valid_pair = false;
    for (std::size_t i = 0; i < counts.size(); ++i) {
        if (counts[i].status == "invalid_read" || counts[i].status == "control_error" || counts[i].status == "system_error") { return 1; }
        if (i%2 == 0 && counts[i].value && counts[i+1].value && *counts[i].value > 0) { valid_pair = true; }
    }
    (void)checksum;
    if (!valid_pair) { std::cout << "SKIP: no reliably scheduled L1D/LL/DTLB read pair\n"; return 77; }
    return 0;
}
