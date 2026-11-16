#pragma once
#include <cstdint>
#include <filesystem>
#include <optional>
#include <string>
#include <vector>
namespace archgraph {
struct CacheEntry {
    std::optional<std::uint64_t> level, size_bytes, line_bytes;
    std::string type, shared_cpu_list, source;
};
struct CacheInfo {
    std::optional<int> source_cpu;
    std::string source, status;
    std::vector<CacheEntry> entries;
};
std::optional<std::uint64_t> parse_cache_size(const std::string& text);
CacheInfo discover_caches(const std::filesystem::path& directory = {});
std::string cache_json(const CacheInfo& info);
struct CachePlan { std::vector<std::uint64_t> sizes; std::string mode; unsigned omitted_targets = 0; };
CachePlan cache_plan(const CacheInfo& info, const std::vector<std::uint64_t>& explicit_sizes, std::uint64_t maximum);
}
