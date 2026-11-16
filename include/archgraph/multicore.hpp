#pragma once
#include <cstdint>
#include <optional>
#include <ostream>
#include <string>
#include <vector>
namespace archgraph::multicore {
std::vector<int> parse_cpu_list(const std::string& text);
std::optional<double> parse_quota(const std::string& quota, const std::string& period = "");
struct Topology {
    unsigned logical = 0;
    std::vector<int> available_cpus;
    std::optional<unsigned> physical_cores, sockets;
    std::optional<bool> smt;
    std::optional<double> quota_cpus;
    bool affinity_known = false, quota_known = false;
    unsigned safe_threads = 1;
    std::vector<std::string> limitations;
};
Topology discover(const std::string& sys = "/sys", const std::string& proc = "/proc");
std::string topology_json(const Topology& topology);
std::vector<int> parse_threads(const std::string& text, unsigned safe, bool oversubscribe);
struct Slot { unsigned block; int threads; bool warmup; };
std::vector<Slot> schedule(const std::vector<int>& threads, unsigned blocks, unsigned warmups, std::uint64_t seed);
struct Summary { double median, minimum, maximum, mad; };
Summary summarize(std::vector<double> values);
std::optional<double> speedup(double baseline, double time);
std::optional<double> efficiency(double baseline, double time, int threads);
std::optional<double> amdahl(double fraction, int threads);
int cli(int argc, char* argv[], std::ostream& out);
}
