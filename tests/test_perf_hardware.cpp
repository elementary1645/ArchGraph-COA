#include "archgraph/perf.hpp"
#include <iostream>
int main() {
    using namespace archgraph::perf;
    Session session;
    session.start();
    volatile std::uint64_t sink = 1;
    for (std::uint64_t i = 1; i < 1000000; ++i) { sink = sink * 1664525 + i; }
    const auto counts = session.stop();
    std::cout << counters_json(counts) << '\n';
    if (!counts[0].value || !counts[1].value) {
        for (const auto& count : counts) {
            if (count.status == "invalid_read" || count.status == "control_error" || count.status == "system_error") {
                std::cerr << "Unexpected PMU syscall failure\n"; return 1;
            }
        }
        std::cout << "SKIP: hardware cycle/instruction pair inaccessible or not reliably scheduled\n";
        return 77;
    }
    if (*counts[0].value <= 0 || *counts[1].value <= 0 || !ratio(counts[1],counts[0])) { return 1; }
    (void)sink;
    return 0;
}
