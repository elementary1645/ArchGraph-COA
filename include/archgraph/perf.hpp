#pragma once
#include <array>
#include <cstddef>
#include <cstdint>
#include <optional>
#include <string>

namespace archgraph::perf {
enum class Event : unsigned { cycles, instructions, cache_references, cache_misses, branches, branch_misses, l1d_reads, l1d_read_misses, ll_reads, ll_read_misses, dtlb_reads, dtlb_read_misses };
enum class EventSet { generic, memory };
Event event_at(std::size_t index, EventSet set);
struct Encoding { std::uint32_t type; std::uint64_t config; };
Encoding encoding(Event event);
constexpr std::size_t event_count = 6;
const char* name(Event event);
enum class Action { reset, enable, disable };
// Injectable syscall boundary. Implementations return -1 and set errno on failure.
class Backend {
public:
    virtual ~Backend() = default;
    virtual int open(Event event, int group_fd) = 0;
    virtual int control(int fd, Action action) = 0;
    virtual std::ptrdiff_t read(int fd, std::uint64_t* data, std::size_t bytes) = 0;
    virtual void close(int fd) noexcept = 0;
};
Backend& system_backend();
struct Counter {
    std::string status = "not_requested";
    std::string diagnostic;
    int error_number = 0;
    std::optional<std::uint64_t> raw, time_enabled, time_running;
    std::optional<double> value;
};
using Counters = std::array<Counter, event_count>;
Counters detect(Backend& backend = system_backend(), EventSet set = EventSet::generic);
// No copy/move: descriptors and backend lifetime stay bound to the creating thread.
class Session {
public:
    explicit Session(Backend& backend = system_backend(), EventSet set = EventSet::generic);
    ~Session();
    Session(const Session&) = delete;
    Session& operator=(const Session&) = delete;
    void start();
    Counters stop();
    const Counters& availability() const { return counters_; }
private:
    struct Group {
        std::array<int, 2> fds{{-1, -1}};
        std::array<std::size_t, 2> indices{};
        std::size_t size = 0;
        bool active = false;
    };
    Backend& backend_;
    std::array<Group, 3> groups_{};
    Counters counters_{};
    bool started_ = false, stopped_ = false;
    void fail(Group& group, const std::string& status, int error);
};
Counter scale(std::uint64_t raw, std::uint64_t enabled, std::uint64_t running);
std::optional<double> ratio(const Counter& numerator, const Counter& denominator);
std::string counters_json(const Counters& counters, EventSet set = EventSet::generic);
std::string derived_json(const Counters& counters, EventSet set = EventSet::generic);
std::string overall_status(const Counters& counters);
Counters unavailable(const std::string& status, const std::string& reason);
std::string diagnostics();
std::string json_quote(const std::string& value);
}
