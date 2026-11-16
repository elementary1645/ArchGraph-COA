#include "archgraph/cache.hpp"
#include "archgraph/perf.hpp"
#include <algorithm>
#include <charconv>
#include <fstream>
#include <set>
#include <sstream>
#include <stdexcept>
#ifdef __linux__
#include <sched.h>
#endif
namespace archgraph {
namespace {
std::string read_field(const std::filesystem::path& path) {
    std::ifstream file(path); std::string value;
    if (!std::getline(file, value) || value.size() > 4096) { return {}; }
    while (!value.empty() && (value.back() == ' ' || value.back() == '\r' || value.back() == '\t')) { value.pop_back(); }
    return value;
}
std::optional<std::uint64_t> decimal(const std::string& text) {
    if (text.empty() || text.front() < '0' || text.front() > '9') { return {}; }
    std::uint64_t value = 0;
    const auto result = std::from_chars(text.data(), text.data()+text.size(), value);
    if (result.ec != std::errc{} || result.ptr != text.data()+text.size() || value == 0) { return {}; }
    return value;
}
void number(std::ostream& out, std::optional<std::uint64_t> value) { if (value) { out << *value; } else { out << "null"; } }
}
std::optional<std::uint64_t> parse_cache_size(const std::string& text) {
    if (text.empty()) { return {}; }
    std::string digits = text;
    std::uint64_t multiplier = 1;
    if (digits.back() == 'K' || digits.back() == 'M' || digits.back() == 'G') {
        multiplier = digits.back() == 'K' ? 1024ULL : (digits.back() == 'M' ? 1024ULL*1024 : 1024ULL*1024*1024);
        digits.pop_back();
    }
    auto value = decimal(digits);
    if (!value || *value > UINT64_MAX / multiplier) { return {}; }
    return *value * multiplier;
}
CacheInfo discover_caches(const std::filesystem::path& directory) {
    CacheInfo info;
    auto path = directory;
    if (path.empty()) {
#ifdef __linux__
        const int cpu = sched_getcpu();
        if (cpu >= 0) {
            info.source_cpu = cpu;
            path = "/sys/devices/system/cpu/cpu" + std::to_string(cpu) + "/cache";
        }
#endif
    }
    info.source = path.string();
    std::error_code error;
    std::vector<std::filesystem::path> indices;
    if (!path.empty()) {
        for (std::filesystem::directory_iterator it(path, error), end; !error && it != end; it.increment(error)) {
            const auto name = it->path().filename().string();
            if (name.size() > 5 && name.rfind("index",0) == 0 &&
                std::all_of(name.begin()+5,name.end(),[](char c){return c >= '0' && c <= '9';})) { indices.push_back(it->path()); }
        }
    }
    std::sort(indices.begin(), indices.end());
    bool complete = !error;
    for (const auto& index : indices) {
        CacheEntry entry;
        entry.source = index.string(); entry.level = decimal(read_field(index/"level"));
        entry.type = read_field(index/"type"); entry.size_bytes = parse_cache_size(read_field(index/"size"));
        entry.line_bytes = decimal(read_field(index/"coherency_line_size"));
        entry.shared_cpu_list = read_field(index/"shared_cpu_list");
        complete = complete && entry.level.has_value() && entry.size_bytes.has_value() &&
            entry.line_bytes.has_value() && !entry.type.empty() && !entry.shared_cpu_list.empty();
        info.entries.push_back(std::move(entry));
    }
    info.status = info.entries.empty() ? "unavailable" : (complete ? "available" : "partial");
    return info;
}
std::string cache_json(const CacheInfo& info) {
    std::ostringstream out;
    out << "{\"status\":" << perf::json_quote(info.status) << ",\"source\":" << perf::json_quote(info.source) << ",\"source_cpu\":";
    if (info.source_cpu) { out << *info.source_cpu; } else { out << "null"; }
    out << ",\"entries\":[";
    for (std::size_t i = 0; i < info.entries.size(); ++i) {
        if (i != 0) { out << ','; } const auto& e = info.entries[i];
        out << "{\"level\":"; number(out,e.level); out << ",\"size_bytes\":"; number(out,e.size_bytes);
        out << ",\"line_bytes\":"; number(out,e.line_bytes);
        out << ",\"type\":" << (e.type.empty() ? "null" : perf::json_quote(e.type))
            << ",\"shared_cpu_list\":" << (e.shared_cpu_list.empty() ? "null" : perf::json_quote(e.shared_cpu_list))
            << ",\"source\":" << perf::json_quote(e.source) << '}';
    }
    out << "],\"warning\":\"Snapshot for one logical CPU; sharing list is OS-reported, not exclusive capacity or a migration guarantee.\"}";
    return out.str();
}
CachePlan cache_plan(const CacheInfo& info, const std::vector<std::uint64_t>& explicit_sizes, std::uint64_t maximum) {
    if (maximum < 8 || maximum > 256ULL*1024*1024 || maximum % 8 != 0) { throw std::invalid_argument("max-size must be 8-byte aligned in [8,268435456]"); }
    CachePlan plan;
    std::set<std::uint64_t> sizes;
    if (!explicit_sizes.empty()) {
        plan.mode = "explicit";
        for (auto size : explicit_sizes) {
            if (size < 8 || size > maximum || size % 8 != 0 || !sizes.insert(size).second) {
                throw std::invalid_argument("sizes must be distinct aligned bytes within max-size");
            }
        }
    } else {
        plan.mode = "discovered";
        for (const auto& e : info.entries) {
            if (!e.size_bytes || !e.level || (e.type != "Data" && e.type != "Unified")) { continue; }
            for (const unsigned factor : {1U,2U,4U}) {
                // 0.5x, 1x and 2x reported capacity, rounded down to an element.
                if (*e.size_bytes > UINT64_MAX/factor) { ++plan.omitted_targets; continue; }
                const auto size = ((*e.size_bytes * factor / 2) / 8) * 8;
                if (size >= 8 && size <= maximum) { sizes.insert(size); } else { ++plan.omitted_targets; }
            }
        }
        if (sizes.empty()) {
            plan.mode = "fallback_configurable_not_cache_capacities";
            for (const auto size : {4096ULL,65536ULL,1048576ULL,8388608ULL}) { if (size <= maximum) { sizes.insert(size); } }
            if (sizes.empty()) { sizes.insert(maximum); }
        }
    }
    plan.sizes.assign(sizes.begin(),sizes.end()); return plan;
}
}
