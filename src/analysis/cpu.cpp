#include "archgraph/analysis.hpp"
#include <omp.h>
#include <fstream>
#include <sstream>
#include <thread>
namespace archgraph {
namespace {
std::string quote(const std::string& value) {
    std::string out = "\"";
    constexpr char hex[] = "0123456789abcdef";
    for (const unsigned char c : value) {
        if (c == '"' || c == '\\') { out += '\\'; out += static_cast<char>(c); }
        else if (c < 32) { out += "\\u00"; out += hex[c >> 4]; out += hex[c & 15]; }
        else { out += static_cast<char>(c); }
    }
    return out + '"';
}
}
std::string cpu_metadata() {
    std::string model;
#ifdef __linux__
    std::ifstream info("/proc/cpuinfo");
    std::string line;
    while (std::getline(info, line)) {
        if (line.rfind("model name", 0) == 0) {
            const auto colon = line.find(':');
            if (colon != std::string::npos) { model = line.substr(colon + 1); }
            break;
        }
    }
#endif
    std::ostringstream out;
    out << "{\"schema_version\":1,\"cpu_model\":" << (model.empty() ? "null" : quote(model))
        << ",\"cpu_model_source\":" << (model.empty() ? "null" : "\"/proc/cpuinfo\"")
        << ",\"logical_cpu_hint\":" << std::thread::hardware_concurrency()
        << ",\"openmp_max_threads\":" << omp_get_max_threads()
        << ",\"openmp_spec\":" << _OPENMP
        << ",\"compiler\":" << quote(__VERSION__)
        << ",\"build_type\":" << quote(ARCHGRAPH_BUILD_TYPE)
        << ",\"clock\":\"std::chrono::steady_clock\",\"hardware_counters_available\":null}";
    return out.str();
}
}
