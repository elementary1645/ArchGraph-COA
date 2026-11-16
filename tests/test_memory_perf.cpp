#include "archgraph/perf.hpp"
#include "test_support.hpp"
#include <cerrno>
#include <map>
#ifdef __linux__
#include <linux/perf_event.h>
#endif
using namespace archgraph::perf;
using dynagraph::test::require;
namespace {
class MemoryBackend final : public Backend {
public:
    bool denied = false, malformed = false;
    unsigned closes = 0, opens = 0;
    std::map<int,unsigned> sizes;
    int open(Event event, int leader) override {
        ++opens; const int fd = static_cast<int>(event);
        require(fd >= 6 && fd < 12, "Memory event mapping");
        if (denied) { errno = EACCES; return -1; }
        ++sizes[leader < 0 ? fd : leader]; return fd;
    }
    int control(int,Action) override {return 0;}
    std::ptrdiff_t read(int fd,std::uint64_t* data,std::size_t bytes) override {
        data[0] = sizes.at(fd); data[1] = 100; data[2] = 50; data[3] = 100; data[4] = 25;
        return malformed ? 0 : static_cast<std::ptrdiff_t>(bytes);
    }
    void close(int) noexcept override {++closes;}
};
}
int main() {
    return dynagraph::test::run("memory PMU encoding, reuse, null fallback and cleanup", [] {
#ifdef __linux__
        const auto access = encoding(Event::l1d_reads), miss = encoding(Event::ll_read_misses);
        require(access.type == PERF_TYPE_HW_CACHE && access.config == (PERF_COUNT_HW_CACHE_L1D | (PERF_COUNT_HW_CACHE_OP_READ<<8) | (PERF_COUNT_HW_CACHE_RESULT_ACCESS<<16)), "L1D read encoding");
        require(miss.config == (PERF_COUNT_HW_CACHE_LL | (PERF_COUNT_HW_CACHE_OP_READ<<8) | (PERF_COUNT_HW_CACHE_RESULT_MISS<<16)), "LL miss encoding");
#endif
        for (int mode = 0; mode < 3; ++mode) {
            MemoryBackend backend; backend.denied = mode == 1; backend.malformed = mode == 2;
            {
                Session session(backend,EventSet::memory); session.start(); const auto c = session.stop();
                require(backend.opens == 6, "All memory events attempted independently");
                if (mode == 0) {
                    require(c[0].value == 200 && c[1].value == 50, "Shared scaling policy");
                    require(derived_json(c,EventSet::memory).find("\"l1d_read_miss_ratio\":0.25") != std::string::npos, "Memory ratios");
                } else {
                    for (const auto& counter : c) { require(!counter.value, "Denied/invalid numeric nulls"); }
                }
                require(counters_json(c,EventSet::memory).find("l1d_read_accesses") != std::string::npos, "Named memory events");
            }
            require(backend.closes == (mode == 1 ? 0U : 6U), "Shared RAII cleanup");
        }
    });
}
