#include "archgraph/experiments.hpp"
#include <charconv>
#include <map>
#include <set>
#include <stdexcept>
#include <string_view>
namespace archgraph {
std::string experiment_help() {
    return "Usage: archgraph memory --input graph.txt\n"
           "Usage: archgraph compare-layouts --input graph.txt [--source 0] [measurement options]\n"
           "Usage: archgraph locality --pattern sequential|strided|random --size BYTES [--stride ELEMENTS] [--seed UINT64] [--accesses N] [measurement options]\n"
           "Usage: archgraph locality --pattern temporal --size BYTES --working-set BYTES [--seed UINT64] [--accesses N] [measurement options]\n"
           "Usage: archgraph locality --pattern csr|adjacency --input graph.txt [--passes 1] [measurement options]\n"
           "Usage: archgraph cache-study [--sizes BYTES,BYTES,...] [--max-size 67108864] [--cache-root SYSFS_CACHE_DIRECTORY] [--seed 1] [--accesses N] [measurement options]\n"
           "Measurement options: --repetitions 5 (alias --runs), --warmups 1, --hardware-counters.\n"
           "Sizes are bytes, multiples of 8 in [8,268435456]. Stride is in elements, positive.\n"
           "Arrays use explicit indexed scalar reads for all patterns. Setup is excluded.\n"
           "Cache-study uses random full permutations, equal read counts and metadata-derived sizes; --max-size bounds data bytes, not total storage.\n"
           "All experiment commands accept --help. Unavailable counters are null. No cache transition is inferred from timing.\n";
}
namespace {
template<class T> void parse(std::string_view text, T& target) {
    if (text.empty() || text.front() < '0' || text.front() > '9') { throw std::invalid_argument("Expected unsigned decimal integer"); }
    const auto parsed = std::from_chars(text.data(),text.data()+text.size(),target);
    if (parsed.ec != std::errc{} || parsed.ptr != text.data()+text.size()) { throw std::invalid_argument("Malformed or out-of-range integer"); }
}
}
int experiment_cli(int argc, char* argv[], std::ostream& output) {
    if (argc == 3 && std::string_view(argv[2]) == "--help") { output << experiment_help(); return output ? 0 : 2; }
    const std::string command(argv[1]);
    std::map<std::string,std::string> args;
    bool hardware = false;
    for (int i = 2; i < argc;) {
        std::string key(argv[i++]);
        if (key == "--hardware-counters") {
            if (hardware) { throw std::invalid_argument("Duplicate --hardware-counters"); } hardware = true; continue;
        }
        if (key == "--runs") { key = "--repetitions"; }
        if (i == argc || !args.emplace(key,argv[i++]).second) { throw std::invalid_argument("Missing value or duplicate option"); }
    }
    std::set<std::string> allowed;
    if (command == "memory") { allowed = {"--input"}; }
    else {
        allowed = {"--repetitions","--warmups"};
        if (command == "compare-layouts") { allowed.insert({"--input","--source"}); }
        else if (command == "locality") {
            allowed.insert("--pattern");
            const auto pattern = args.count("--pattern") ? args.at("--pattern") : "sequential";
            if (pattern == "csr" || pattern == "adjacency") { allowed.insert({"--input","--passes"}); }
            else {
                allowed.insert({"--size","--seed","--accesses"});
                if (pattern == "strided") { allowed.insert("--stride"); }
                if (pattern == "temporal") { allowed.insert("--working-set"); }
            }
        } else if (command == "cache-study") { allowed.insert({"--sizes","--max-size","--cache-root","--seed","--accesses"}); }
        else { throw std::invalid_argument("Unknown experiment command"); }
    }
    if (hardware && command == "memory") { throw std::invalid_argument("memory does not execute a hardware-counter measurement"); }
    for (const auto& arg : args) { if (allowed.count(arg.first) == 0) { throw std::invalid_argument("Unknown or inapplicable option: " + arg.first); } }
    ExperimentOptions o; o.hardware_counters = hardware;
    const auto number = [&](const char* key, auto& target) { if (args.count(key)) { parse(args.at(key),target); } };
    number("--source",o.source); number("--size",o.size); number("--working-set",o.working_set);
    number("--stride",o.stride); number("--seed",o.seed); number("--accesses",o.accesses);
    number("--repetitions",o.repetitions); number("--warmups",o.warmups); number("--passes",o.passes); number("--max-size",o.maximum);
    if (args.count("--accesses") && o.accesses == 0) { throw std::invalid_argument("accesses must be positive"); }
    if (o.stride == 0) { throw std::invalid_argument("stride must be positive"); }
    if (args.count("--input")) { o.input = args.at("--input"); }
    if (args.count("--pattern")) { o.pattern = args.at("--pattern"); }
    if (args.count("--cache-root")) { o.cache_root = args.at("--cache-root"); if (o.cache_root.empty()) { throw std::invalid_argument("Empty cache-root"); } }
    if (args.count("--sizes")) {
        const auto& text = args.at("--sizes"); std::size_t begin = 0;
        do {
            const auto end = text.find(',',begin); std::uint64_t value = 0;
            parse(std::string_view(text).substr(begin,end == std::string::npos ? end : end-begin),value);
            o.sizes.push_back(value);
            if (o.sizes.size() > 64) { throw std::invalid_argument("At most 64 explicit sizes"); }
            if (end == std::string::npos) { break; } begin = end+1;
        } while (true);
    }
    return experiment_command(command,o,output);
}
}
