#include "archgraph/perf.hpp"
#include "archgraph/analysis.hpp"
#include <cerrno>
#include <cmath>
#include <cstring>
#include <fstream>
#include <iomanip>
#include <sstream>
#include <stdexcept>
#ifdef __linux__
#include <linux/perf_event.h>
#include <sys/ioctl.h>
#include <sys/syscall.h>
#include <sys/utsname.h>
#include <unistd.h>
#include <sched.h>
#endif

namespace archgraph::perf {
namespace {
class SystemBackend final : public Backend {
public:
    int open(Event event, int group_fd) override {
#ifdef __linux__
        const auto event_config = encoding(event);
        perf_event_attr attr{};
        attr.type = event_config.type;
        attr.size = sizeof(attr);
        attr.config = event_config.config;
        attr.disabled = 1;
        attr.exclude_kernel = 1;
        attr.exclude_hv = 1;
        attr.inherit = 0;
        attr.read_format = PERF_FORMAT_GROUP | PERF_FORMAT_TOTAL_TIME_ENABLED | PERF_FORMAT_TOTAL_TIME_RUNNING;
        return static_cast<int>(syscall(SYS_perf_event_open, &attr, 0, -1, group_fd, PERF_FLAG_FD_CLOEXEC));
#else
        (void)event; (void)group_fd; errno = ENOSYS; return -1;
#endif
    }
    int control(int fd, Action action) override {
#ifdef __linux__
        const unsigned long request = action == Action::reset ? PERF_EVENT_IOC_RESET :
            (action == Action::enable ? PERF_EVENT_IOC_ENABLE : PERF_EVENT_IOC_DISABLE);
        return ioctl(fd, request, PERF_IOC_FLAG_GROUP);
#else
        (void)fd; (void)action; errno = ENOSYS; return -1;
#endif
    }
    std::ptrdiff_t read(int fd, std::uint64_t* data, std::size_t bytes) override {
#ifdef __linux__
        return ::read(fd, data, bytes);
#else
        (void)fd; (void)data; (void)bytes; errno = ENOSYS; return -1;
#endif
    }
    void close(int fd) noexcept override {
#ifdef __linux__
        (void)::close(fd); // Never retry close: EINTR may already have released fd.
#else
        (void)fd;
#endif
    }
};
std::string error_status(int error) {
    if (error == EPERM || error == EACCES) { return "permission_denied"; }
    if (error == ENOSYS || error == ENODEV || error == ENOENT || error == EOPNOTSUPP || error == EINVAL) {
        return "unsupported";
    }
    return "system_error";
}
void number(std::ostream& out, const std::optional<double>& value) {
    if (value) { out << std::setprecision(17) << *value; } else { out << "null"; }
}
void integer(std::ostream& out, const std::optional<std::uint64_t>& value) {
    if (value) { out << *value; } else { out << "null"; }
}
}
Backend& system_backend() { static SystemBackend backend; return backend; }
const char* name(Event event) {
    constexpr std::array<const char*, 12> names{{"cpu_cycles", "instructions", "cache_references", "cache_misses", "branch_instructions", "branch_misses", "l1d_read_accesses", "l1d_read_misses", "ll_read_accesses", "ll_read_misses", "dtlb_read_accesses", "dtlb_read_misses"}};
    return names.at(static_cast<std::size_t>(event));
}
std::string json_quote(const std::string& value) {
    std::string out = "\"";
    constexpr char hex[] = "0123456789abcdef";
    for (const unsigned char c : value) {
        if (c == '"' || c == '\\') { out += '\\'; out += static_cast<char>(c); }
        else if (c < 32) { out += "\\u00"; out += hex[c >> 4]; out += hex[c & 15]; }
        else { out += static_cast<char>(c); }
    }
    return out + '"';
}
Event event_at(std::size_t index, EventSet set) {
    if (index >= event_count) { throw std::out_of_range("counter slot"); }
    return static_cast<Event>(index + (set == EventSet::memory ? event_count : 0));
}
Encoding encoding(Event event) {
#ifdef __linux__
    constexpr std::array<std::uint64_t, event_count> generic{{PERF_COUNT_HW_CPU_CYCLES, PERF_COUNT_HW_INSTRUCTIONS,
        PERF_COUNT_HW_CACHE_REFERENCES, PERF_COUNT_HW_CACHE_MISSES, PERF_COUNT_HW_BRANCH_INSTRUCTIONS, PERF_COUNT_HW_BRANCH_MISSES}};
    const auto index = static_cast<std::size_t>(event);
    if (index < event_count) { return {PERF_TYPE_HARDWARE, generic.at(index)}; }
    if (index >= 12) { throw std::out_of_range("hardware event"); }
    const std::array<std::uint64_t, 3> levels{{PERF_COUNT_HW_CACHE_L1D, PERF_COUNT_HW_CACHE_LL, PERF_COUNT_HW_CACHE_DTLB}};
    const auto slot = index - event_count;
    return {PERF_TYPE_HW_CACHE, levels.at(slot / 2) | (static_cast<std::uint64_t>(PERF_COUNT_HW_CACHE_OP_READ) << 8) |
        (static_cast<std::uint64_t>(slot % 2 == 0 ? PERF_COUNT_HW_CACHE_RESULT_ACCESS : PERF_COUNT_HW_CACHE_RESULT_MISS) << 16)};
#else
    (void)event; return {0, 0}; // Backend returns ENOSYS before using this on non-Linux.
#endif
}
Counters detect(Backend& backend, EventSet set) {
    Counters counters;
    for (std::size_t i = 0; i < event_count; ++i) {
        const int fd = backend.open(event_at(i, set), -1);
        if (fd >= 0) {
            backend.close(fd);
            counters[i].status = "ready";
        } else {
            const int error = errno;
            counters[i].error_number = error;
            counters[i].status = error_status(error);
            counters[i].diagnostic = std::strerror(error);
        }
    }
    return counters;
}
Session::Session(Backend& backend, EventSet set) : backend_(backend) {
    // Each event is attempted even if its partner failed. Surviving events become
    // singleton groups; unavailable partners never acquire fabricated values.
    try {
        for (std::size_t pair = 0; pair < groups_.size(); ++pair) {
            auto& group = groups_[pair];
            for (std::size_t offset = 0; offset < 2; ++offset) {
                const auto index = pair * 2 + offset;
                const int fd = backend_.open(event_at(index, set), group.size == 0 ? -1 : group.fds[0]);
                auto& counter = counters_[index];
                if (fd < 0) {
                    counter.error_number = errno;
                    counter.status = error_status(errno);
                    counter.diagnostic = std::strerror(counter.error_number);
                } else {
                    // Store ownership before any allocating operation.
                    group.fds[group.size] = fd;
                    group.indices[group.size++] = index;
                    counter.status = "ready";
                }
            }
        }
    } catch (...) {
        for (auto& group : groups_) {
            for (std::size_t i = group.size; i > 0; --i) { backend_.close(group.fds[i - 1]); }
        }
        throw;
    }
}
Session::~Session() {
    for (auto& group : groups_) {
        // Closing all events also stops counting after exceptional algorithm exits.
        for (std::size_t i = group.size; i > 0; --i) { backend_.close(group.fds[i - 1]); }
    }
}
void Session::fail(Group& group, const std::string& status, int error) {
    for (std::size_t i = 0; i < group.size; ++i) {
        auto& counter = counters_[group.indices[i]];
        counter.status = status;
        counter.error_number = error;
        counter.diagnostic = error == 0 ? status : std::strerror(error);
        counter.value.reset();
    }
}
void Session::start() {
    if (started_) { throw std::logic_error("Counter session cannot be restarted"); }
    started_ = true;
    for (auto& group : groups_) {
        if (group.size == 0) { continue; }
        if (backend_.control(group.fds[0], Action::reset) < 0 ||
            backend_.control(group.fds[0], Action::enable) < 0) {
            const int error = errno;
            fail(group, "control_error", error);
        } else { group.active = true; }
    }
}
Counter scale(std::uint64_t raw, std::uint64_t enabled, std::uint64_t running) {
    Counter result;
    result.raw = raw; result.time_enabled = enabled; result.time_running = running;
    if (enabled == 0 || running == 0 || running > enabled) {
        result.status = "invalid_timing"; result.diagnostic = "zero or inconsistent scheduling times";
        return result;
    }
    // Conservative quality gate: below 10% residency extrapolation is unreliable.
    if (static_cast<long double>(running) / enabled < 0.1L) {
        result.status = "unreliable"; result.diagnostic = "PMU running fraction below 0.1";
        return result;
    }
    const double value = static_cast<double>(static_cast<long double>(raw) * enabled / running);
    if (!std::isfinite(value)) { result.status = "invalid_value"; return result; }
    result.value = value;
    result.status = running == enabled ? "available" : "multiplexed";
    return result;
}
Counters Session::stop() {
    if (!started_ || stopped_) { throw std::logic_error("Counter session must start and stop once"); }
    stopped_ = true;
    for (auto& group : groups_) {
        if (!group.active) { continue; }
        group.active = false;
        if (backend_.control(group.fds[0], Action::disable) < 0) {
            const int error = errno; fail(group, "control_error", error); continue;
        }
        std::array<std::uint64_t, 5> data{};
        const auto expected = (3 + group.size) * sizeof(std::uint64_t);
        std::ptrdiff_t bytes;
        do { bytes = backend_.read(group.fds[0], data.data(), expected); } while (bytes < 0 && errno == EINTR);
        if (bytes != static_cast<std::ptrdiff_t>(expected) || data[0] != group.size) {
            const int error = bytes < 0 ? errno : 0;
            fail(group, "invalid_read", error); continue;
        }
        // PERF_FORMAT_GROUP returns values in event creation order.
        for (std::size_t i = 0; i < group.size; ++i) {
            counters_[group.indices[i]] = scale(data[3 + i], data[1], data[2]);
        }
    }
    return counters_;
}
std::optional<double> ratio(const Counter& numerator, const Counter& denominator) {
    if (!numerator.value || !denominator.value || *denominator.value <= 0) { return {}; }
    const double result = *numerator.value / *denominator.value;
    return std::isfinite(result) ? std::optional<double>(result) : std::nullopt;
}
Counters unavailable(const std::string& status, const std::string& reason) {
    Counters counters;
    for (auto& counter : counters) { counter.status = status; counter.diagnostic = reason; }
    return counters;
}
std::string overall_status(const Counters& counters) {
    std::size_t valid = 0;
    bool multiplexed = false;
    for (const auto& c : counters) { valid += c.value.has_value() ? 1U : 0U; multiplexed |= c.status == "multiplexed"; }
    if (valid == event_count) { return multiplexed ? "multiplexed" : "available"; }
    if (valid != 0) { return "partial"; }
    const auto& first = counters[0].status;
    for (const auto& c : counters) { if (c.status != first) { return "unavailable"; } }
    return first;
}
std::string counters_json(const Counters& counters, EventSet set) {
    std::ostringstream out; out << '{';
    for (std::size_t i = 0; i < event_count; ++i) {
        if (i != 0) { out << ','; }
        const auto& c = counters[i];
        out << json_quote(name(event_at(i, set))) << ":{\"status\":" << json_quote(c.status)
            << ",\"errno\":" << c.error_number << ",\"diagnostic\":" << json_quote(c.diagnostic) << ",\"raw\":";
        integer(out, c.raw); out << ",\"time_enabled_ns\":"; integer(out, c.time_enabled);
        out << ",\"time_running_ns\":"; integer(out, c.time_running);
        out << ",\"value\":"; number(out, c.value); out << '}';
    }
    out << '}'; return out.str();
}
std::string derived_json(const Counters& c, EventSet set) {
    if (set == EventSet::memory) {
        std::ostringstream out; out << "{\"l1d_read_miss_ratio\":"; number(out, ratio(c[1],c[0]));
        out << ",\"ll_read_miss_ratio\":"; number(out, ratio(c[3],c[2]));
        out << ",\"dtlb_read_miss_ratio\":"; number(out, ratio(c[5],c[4]));
        out << '}'; return out.str();
    }
    std::ostringstream out; out << "{\"ipc\":"; number(out, ratio(c[1], c[0]));
    out << ",\"cpi\":"; number(out, ratio(c[0], c[1]));
    out << ",\"cache_miss_ratio\":"; number(out, ratio(c[3], c[2]));
    out << ",\"branch_miss_ratio\":"; number(out, ratio(c[5], c[4]));
    out << '}'; return out.str();
}
std::string diagnostics() {
    const auto independent = detect();
    Session session;
    const auto grouped = session.availability();
    session.start();
    volatile std::uint64_t probe = 1;
    for (std::uint64_t i = 1; i < 10000; ++i) { probe = probe * 1664525 + i; }
    const auto readings = session.stop();
    (void)probe;
    std::ostringstream out;
    out << "{\"schema_version\":1,\"status\":\"diagnostic\",\"metadata\":" << cpu_metadata();
#ifdef __linux__
    utsname info{};
    if (uname(&info) == 0) {
        out << ",\"os\":" << json_quote(info.sysname) << ",\"architecture\":" << json_quote(info.machine)
            << ",\"kernel\":" << json_quote(info.release);
    } else { out << ",\"os\":\"Linux\",\"architecture\":null,\"kernel\":null"; }
    cpu_set_t cpus;
    CPU_ZERO(&cpus);
    out << ",\"affinity_logical_processors\":";
    if (sched_getaffinity(0, sizeof(cpus), &cpus) == 0) { out << CPU_COUNT(&cpus); } else { out << "null"; }
#else
    out << ",\"os\":null,\"architecture\":null,\"kernel\":null,\"affinity_logical_processors\":null";
#endif
    std::ifstream setting("/proc/sys/kernel/perf_event_paranoid");
    int paranoid = 0;
    out << ",\"perf_event_paranoid\":";
    if (setting >> paranoid) { out << paranoid; } else { out << "null"; }
    out << ",\"availability\":" << counters_json(independent)
        << ",\"memory_event_availability\":" << counters_json(detect(system_backend(), EventSet::memory), EventSet::memory)
        << ",\"group_availability\":" << counters_json(grouped)
        << ",\"probe_counters\":" << counters_json(readings)
        << ",\"probe_workload\":\"9999-iteration diagnostic arithmetic; not graph benchmark data\""
        << ",\"scope\":\"calling_thread_user_space_no_inheritance\""
        << ",\"warning\":\"ready means open succeeded; only a completed measurement establishes PMU scheduling. No permissions are changed.\"}";
    return out.str();
}
}
