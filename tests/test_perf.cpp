#include "archgraph/perf.hpp"
#include "test_support.hpp"
#include <algorithm>
#include <cerrno>
#include <cmath>
#include <map>
#include <stdexcept>
#include <vector>
using namespace archgraph::perf;
using dynagraph::test::require;
namespace {
class Fake final : public Backend {
public:
    std::array<int, event_count> errors{};
    std::vector<int> attempted, closed;
    std::map<int, std::vector<Event>> groups;
    std::vector<int> live;
    int fail_action = -1;
    bool control_failure = false, short_read = false, bad_nr = false, read_failure = false;
    bool interrupt_read = false;
    int throw_on_event = -1;
    unsigned controls = 0;
    int open(Event event, int leader) override {
        const int index = static_cast<int>(event);
        attempted.push_back(index);
        if (index == throw_on_event) { throw std::runtime_error("injected constructor failure"); }
        if (errors[static_cast<std::size_t>(index)] != 0) {
            errno = errors[static_cast<std::size_t>(index)]; return -1;
        }
        const int fd = 100 + index;
        live.push_back(fd);
        groups[leader < 0 ? fd : leader].push_back(event);
        return fd;
    }
    int control(int, Action action) override {
        ++controls;
        if (control_failure || static_cast<int>(action) == fail_action) { errno = EIO; return -1; } return 0;
    }
    std::ptrdiff_t read(int fd, std::uint64_t* data, std::size_t bytes) override {
        if (interrupt_read) { interrupt_read = false; errno = EINTR; return -1; }
        if (read_failure) { errno = EIO; return -1; }
        const auto& events = groups.at(fd);
        data[0] = bad_nr ? 99 : events.size(); data[1] = 100; data[2] = 50;
        constexpr std::array<std::uint64_t, event_count> values{{100, 200, 80, 20, 40, 4}};
        for (std::size_t i = 0; i < events.size(); ++i) { data[3 + i] = values[static_cast<std::size_t>(events[i])]; }
        return static_cast<std::ptrdiff_t>(bytes - (short_read ? 8U : 0U));
    }
    void close(int fd) noexcept override {
        closed.push_back(fd);
        const auto found = std::find(live.begin(), live.end(), fd);
        if (found == live.end()) { std::terminate(); }
        live.erase(found);
    }
};
void arithmetic() {
    const auto cycles = scale(100, 100, 50);
    const auto instructions = scale(200, 100, 50);
    require(cycles.value == 200 && cycles.status == "multiplexed", "Multiplexing scale");
    require(ratio(instructions, cycles) == 2 && ratio(cycles, instructions) == 0.5, "IPC and CPI");
    require(ratio(scale(20,100,100), scale(80,100,100)) == 0.25, "Cache miss ratio");
    require(ratio(scale(4,100,100), scale(40,100,100)) == 0.1, "Branch miss ratio");
    require(!ratio(cycles, scale(0,100,100)), "Zero denominator is unavailable");
    require(!ratio(Counter{}, cycles), "Missing numerator is unavailable");
    require(!scale(1,0,0).value && !scale(1,100,0).value, "Unscheduled invalid");
    require(!scale(1,10,11).value, "Inconsistent times invalid");
    require(!scale(1,100,1).value && scale(1,100,1).raw == 1, "Low residency rejected with raw preserved");
    require(scale(UINT64_MAX,100,10).value.has_value(), "Scaling avoids integer overflow");
    require(scale(0,100,100).value == 0, "Real zero count stays valid");
}
void lifecycle() {
    Fake fake;
    {
        Session session(fake);
        require(fake.attempted.size() == 6 && fake.groups.size() == 3, "Six independent opens in three groups");
        dynagraph::test::require_throws<std::logic_error>([&]{session.stop();}, "once");
        session.start(); fake.interrupt_read = true;
        const auto counters = session.stop();
        require(overall_status(counters) == "multiplexed", "All groups read");
        require(counters[1].raw == 200 && counters[1].value == 400, "Creation order maps counts");
        require(derived_json(counters).find("\"ipc\":2") != std::string::npos, "Derived serialization");
        require(counters_json(counters).find("\"time_running_ns\":50") != std::string::npos, "Scheduling serialization");
        dynagraph::test::require_throws<std::logic_error>([&]{session.start();}, "restarted");
        dynagraph::test::require_throws<std::logic_error>([&]{session.stop();}, "once");
    }
    require(fake.live.empty() && fake.closed.size() == 6, "All descriptors closed once");
    Fake throws;
    throws.throw_on_event = 3;
    dynagraph::test::require_throws<std::runtime_error>([&]{Session session(throws);}, "constructor");
    require(throws.live.empty() && throws.closed.size() == 3, "Constructor failure closes acquired descriptors");
    Fake exceptional;
    try { Session session(exceptional); session.start(); throw std::runtime_error("algorithm"); }
    catch (const std::runtime_error&) {}
    require(exceptional.live.empty(), "Exceptional algorithm exit releases active events");
}
void fallback() {
    Fake availability;
    availability.errors[0] = ENODEV;
    const auto available = detect(availability);
    require(available[0].status == "unsupported" && available[1].status == "ready", "Independent availability");
    require(availability.attempted.size() == 6 && availability.closed.size() == 5 && availability.live.empty(), "Availability probe cleanup");
    Fake denied; denied.errors.fill(EPERM);
    { Session session(denied); session.start(); const auto c = session.stop();
      require(overall_status(c) == "permission_denied", "Permission status");
      for (const auto& counter : c) {
          require(!counter.value && !counter.raw && counter.error_number == EPERM, "Denied counts null, errno preserved");
      }
    }
    require(denied.attempted.size() == 6 && denied.closed.empty(), "Permission failures attempted independently");
    Fake mixed; mixed.errors[0] = EACCES; mixed.errors[3] = EOPNOTSUPP;
    { Session session(mixed); session.start(); const auto c = session.stop();
      require(c[0].status == "permission_denied" && c[3].status == "unsupported", "Per event availability");
      require(c[1].raw == 200 && c[2].raw == 80 && overall_status(c) == "partial", "Surviving singleton events valid");
      require(!ratio(c[1],c[0]) && !ratio(c[3],c[2]), "Partial pair ratios null");
    }
    require(mixed.live.empty(), "Partial open cleanup");
    for (int mode = 0; mode < 6; ++mode) {
        Fake broken; broken.short_read = mode == 0; broken.bad_nr = mode == 1;
        broken.read_failure = mode == 2; broken.control_failure = mode == 3;
        broken.fail_action = mode == 4 ? static_cast<int>(Action::enable) :
            (mode == 5 ? static_cast<int>(Action::disable) : -1);
        { Session session(broken); session.start(); const auto c = session.stop();
          for (const auto& counter : c) { require(!counter.value && counter.status != "ready", "Bad read/control never valid"); }
        }
        require(broken.live.empty(), "Error path cleanup");
    }
    Fake exhausted; exhausted.errors.fill(EMFILE);
    require(overall_status(detect(exhausted)) == "system_error", "Resource exhaustion is not mislabeled unsupported");
    require(json_quote("\"\n\\") == "\"\\\"\\u000a\\\\\"", "JSON escaping");
}
}
int main() {
    return dynagraph::test::run("perf availability, cleanup, arithmetic, scaling and failures", [] {
        arithmetic(); lifecycle(); fallback();
    });
}
