#include "archgraph/cache.hpp"
#include "test_support.hpp"
#include <chrono>
#include <fstream>
using namespace archgraph;
using dynagraph::test::require;
int main() {
    return dynagraph::test::run("cache metadata, incomplete discovery and bounded planning", [] {
        require(parse_cache_size("32K") == 32768 && parse_cache_size("2M") == 2097152 && parse_cache_size("64") == 64, "Size units");
        for (const std::string text : {"","0","-1K","garbage","18446744073709551615G","1KB"}) { require(!parse_cache_size(text), "Invalid metadata remains unknown"); }
        struct Temp {
            std::filesystem::path path = std::filesystem::temp_directory_path() / ("archgraph-cache-"+std::to_string(std::chrono::steady_clock::now().time_since_epoch().count()));
            ~Temp() { std::error_code error; std::filesystem::remove_all(path,error); }
        } temp;
        const auto index = temp.path/"index0"; std::filesystem::create_directories(index);
        std::ofstream(index/"level") << "1\n"; std::ofstream(index/"type") << "Data\n";
        std::ofstream(index/"size") << "32K\n"; std::ofstream(index/"coherency_line_size") << "64\n";
        std::ofstream(index/"shared_cpu_list") << "0-1\n";
        auto info = discover_caches(temp.path);
        require(info.status == "available" && info.entries.size() == 1 && info.entries[0].shared_cpu_list == "0-1", "Actual metadata fields and sharing retained");
        auto plan = cache_plan(info,{},1048576);
        require(plan.mode == "discovered" && plan.sizes == std::vector<std::uint64_t>({16384,32768,65536}), "Half, near, above reported capacity");
        std::ofstream(index/"size") << "bad\n";
        info = discover_caches(temp.path);
        require(info.status == "partial" && !info.entries[0].size_bytes, "Partial metadata");
        plan = cache_plan(info,{},1048576);
        require(plan.mode == "fallback_configurable_not_cache_capacities", "Fallback never claims discovered capacities");
        require(discover_caches(temp.path/"missing").status == "unavailable", "Unavailable sysfs");
        require(cache_plan(info,{4096,8192},16384).mode == "explicit", "Explicit fallback sizes");
        std::ofstream(index/"size") << "32K\n";
        plan = cache_plan(discover_caches(temp.path),{},8192);
        require(plan.omitted_targets == 3 && plan.mode == "fallback_configurable_not_cache_capacities", "Omitted metadata targets explicit");
        dynagraph::test::require_throws<std::invalid_argument>([&]{(void)cache_plan(info,{8,8},16);}, "distinct");
        dynagraph::test::require_throws<std::invalid_argument>([&]{(void)cache_plan(info,{24},16);}, "within");
        require(cache_json(info).find("\"size_bytes\":null") != std::string::npos, "Missing numeric metadata null");
    });
}
