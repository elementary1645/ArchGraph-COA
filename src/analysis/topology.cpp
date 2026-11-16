#include "archgraph/multicore.hpp"
#include "archgraph/perf.hpp"
#include <algorithm>
#include <charconv>
#include <cmath>
#include <filesystem>
#include <fstream>
#include <limits>
#include <set>
#include <sstream>
#include <stdexcept>
#include <thread>
#include <omp.h>
#ifdef __linux__
#include <sched.h>
#endif
namespace archgraph::multicore {
namespace {
std::string read(const std::string& path) { std::ifstream f(path); std::ostringstream s; s << f.rdbuf(); return s.str(); }
int integer(const std::string& s) {
    int value = 0; const auto r = std::from_chars(s.data(), s.data()+s.size(), value);
    if (s.empty() || r.ec != std::errc{} || r.ptr != s.data()+s.size() || value < 0) { throw std::invalid_argument("Invalid CPU/thread list"); }
    return value;
}
}
std::vector<int> parse_cpu_list(const std::string& text) {
    std::string clean = text; while (!clean.empty() && (clean.back()=='\n' || clean.back()==' ')) { clean.pop_back(); }
    if (clean.empty()) { throw std::invalid_argument("Empty CPU list"); }
    std::set<int> cpus; std::size_t pos = 0;
    while (pos < clean.size()) {
        const auto end = clean.find(',',pos); const auto part = clean.substr(pos,end-pos); const auto dash = part.find('-');
        const int first = integer(part.substr(0,dash)); const int last = dash == std::string::npos ? first : integer(part.substr(dash+1));
        if (last < first || last > 1048575) { throw std::invalid_argument("CPU range out of bounds"); }
        for (int cpu=first; cpu<=last; ++cpu) { cpus.insert(cpu); }
        if (end == std::string::npos) { break; } pos=end+1;
        if (pos==clean.size()) { throw std::invalid_argument("Trailing CPU separator"); }
    }
    return {cpus.begin(),cpus.end()};
}
std::optional<double> parse_quota(const std::string& quota, const std::string& period) {
    std::istringstream s(quota + (period.empty() ? "" : " " + period)); std::string q, p, extra; s>>q>>p;
    if (q.empty() || p.empty() || (s>>extra)) { throw std::invalid_argument("Malformed CPU quota"); }
    const auto number=[](const std::string& x) { std::int64_t n=0; const auto r=std::from_chars(x.data(),x.data()+x.size(),n); if(r.ec!=std::errc{} || r.ptr!=x.data()+x.size()) { throw std::invalid_argument("Malformed CPU quota number"); } return n; };
    const auto denominator=number(p); if(denominator<=0) { throw std::invalid_argument("Invalid quota period"); }
    if(q=="max" || q=="-1") { return std::nullopt; }
    const auto numerator=number(q); if(numerator<=0) { throw std::invalid_argument("Invalid quota"); }
    return static_cast<double>(numerator)/static_cast<double>(denominator);
}
Topology discover(const std::string& sys, const std::string& proc) {
    Topology t;
    try { t.logical=static_cast<unsigned>(parse_cpu_list(read(sys+"/devices/system/cpu/online")).size()); } catch(const std::exception&) { t.logical=std::thread::hardware_concurrency(); }
#ifdef __linux__
    if(proc=="/proc" && sys=="/sys") {
        // Dynamically sized masks preserve sparse IDs and machines larger than CPU_SETSIZE.
        for(std::size_t count=128; count<=1048576; count*=2) {
            cpu_set_t* mask=CPU_ALLOC(count); if(!mask) { break; } const auto bytes=CPU_ALLOC_SIZE(count); CPU_ZERO_S(bytes,mask);
            if(sched_getaffinity(0,bytes,mask)==0) {
                for(std::size_t i=0;i<count;++i) { if(CPU_ISSET_S(i,bytes,mask)) { t.available_cpus.push_back(static_cast<int>(i)); } }
                t.affinity_known=true; CPU_FREE(mask); break;
            } CPU_FREE(mask);
        }
    } else
#endif
    {
        std::istringstream status(read(proc+"/self/status")); std::string line;
        while(std::getline(status,line)) { if(line.rfind("Cpus_allowed_list:",0)==0) { try { auto value=line.substr(line.find(':')+1); value.erase(0,value.find_first_not_of(" \t")); t.available_cpus=parse_cpu_list(value); t.affinity_known=true; } catch(const std::exception&) {} } }
    }
    std::set<std::pair<int,int>> cores; std::set<int> sockets; bool complete=!t.available_cpus.empty(); bool smt=false;
    for(const int cpu:t.available_cpus) {
        const auto root=sys+"/devices/system/cpu/cpu"+std::to_string(cpu)+"/topology/";
        try {
            std::istringstream c(read(root+"core_id")),p(read(root+"physical_package_id")); int core=-1,package=-1;
            if(!(c>>core) || !(p>>package) || core<0 || package<0) { complete=false; continue; }
            cores.insert({package,core}); sockets.insert(package);
            if(parse_cpu_list(read(root+"thread_siblings_list")).size()>1) { smt=true; }
        } catch(const std::exception&) { complete=false; }
    }
    if(complete) { t.physical_cores=static_cast<unsigned>(cores.size()); t.sockets=static_cast<unsigned>(sockets.size()); t.smt=smt;
        if(cores.size()<t.available_cpus.size()) { t.limitations.push_back("Available logical processors share physical cores (SMT); thread count is not independent core count"); }
    }
    // Probe current cgroup and every visible ancestor, retaining the strictest quota.
    std::istringstream groups(read(proc+"/self/cgroup")); std::string line;
    std::vector<std::pair<std::string,bool>> paths;
    while(std::getline(groups,line)) {
        const auto first=line.find(':'),second=line.find(':',first==std::string::npos?0:first+1);
        if(second==std::string::npos) { continue; }
        const auto controllers=line.substr(first+1,second-first-1); const auto relative=line.substr(second+1);
        if(relative.find("..")!=std::string::npos) { t.limitations.push_back("cgroup path outside visible namespace; ancestor quotas may be hidden"); continue; }
        if(controllers.empty()) { paths.push_back({sys+"/fs/cgroup"+relative,true}); }
        else if((","+controllers+",").find(",cpu,")!=std::string::npos) { paths.push_back({sys+"/fs/cgroup/cpu"+relative,false}); paths.push_back({sys+"/fs/cgroup/cpu,cpuacct"+relative,false}); }
    }
    paths.push_back({sys+"/fs/cgroup",true}); paths.push_back({sys+"/fs/cgroup/cpu",false});
    for(const auto& entry:paths) {
        std::filesystem::path path(entry.first); const auto root=std::filesystem::path(sys+"/fs/cgroup");
        while(path.string().size()>=root.string().size()) {
            const auto q=read(path.string()+(entry.second?"/cpu.max":"/cpu.cfs_quota_us"));
            if(!q.empty()) { try { const auto value=parse_quota(q,entry.second?"":read(path.string()+"/cpu.cfs_period_us")); t.quota_known=true; if(value && (!t.quota_cpus || *value<*t.quota_cpus)) { t.quota_cpus=value; } } catch(const std::exception&) { t.limitations.push_back("Malformed visible cgroup CPU quota"); } }
            if(path==root) { break; } const auto parent=path.parent_path(); if(parent==path) { break; } path=parent;
        }
    }
    unsigned limit=t.affinity_known?static_cast<unsigned>(t.available_cpus.size()):1;
    if(t.quota_cpus) { limit=std::min(limit,static_cast<unsigned>(std::max(1.0,std::min(1048576.0,std::floor(*t.quota_cpus))))); }
    t.safe_threads=std::max(1U,std::min(limit,static_cast<unsigned>(omp_get_thread_limit())));
    if(!t.affinity_known) { t.limitations.push_back("Affinity unavailable; conservative one-thread default"); }
    if(!complete) { t.limitations.push_back("Physical core/socket/SMT topology unavailable or incomplete"); }
    if(!t.quota_known) { t.limitations.push_back("CPU quota unavailable"); }
    t.limitations.push_back("Visible topology and quotas do not establish dedicated cores; hidden ancestor limits and shared-host interference are possible");
    return t;
}
std::string topology_json(const Topology& t) {
    std::ostringstream o; o<<"{\"logical_processors\":"; if(t.logical) { o<<t.logical; } else { o<<"null"; } o<<",\"physical_cores_in_affinity\":";
    if(t.physical_cores) { o<<*t.physical_cores; } else { o<<"null"; }
    o<<",\"sockets_in_affinity\":"; if(t.sockets) { o<<*t.sockets; } else { o<<"null"; }
    o<<",\"smt_detected\":"; if(t.smt) { o<<(*t.smt?"true":"false"); } else { o<<"null"; }
    o<<",\"affinity_known\":"<<(t.affinity_known?"true":"false")<<",\"available_cpus\":[";
    for(std::size_t i=0;i<t.available_cpus.size();++i) { if(i) { o<<','; } o<<t.available_cpus[i]; }
    o<<"],\"affinity_restricted\":"; if(t.affinity_known && t.logical) { o<<(t.available_cpus.size()<t.logical?"true":"false"); } else { o<<"null"; }
    o<<",\"quota_status\":"<<perf::json_quote(t.quota_known?(t.quota_cpus?"limited":"unlimited_visible"):"unavailable")<<",\"quota_cpus\":";
    if(t.quota_cpus) { o<<*t.quota_cpus; } else { o<<"null"; }
    o<<",\"safe_thread_limit\":"<<t.safe_threads<<",\"limitations\":[";
    for(std::size_t i=0;i<t.limitations.size();++i) { if(i) { o<<','; } o<<perf::json_quote(t.limitations[i]); } o<<"]}"; return o.str();
}
std::vector<int> parse_threads(const std::string& text,unsigned safe,bool oversubscribe) {
    std::vector<int> result; std::istringstream s(text); std::string part;
    while(std::getline(s,part,',')) { const int n=integer(part); if(n<1 || n>4096 || (!oversubscribe && static_cast<unsigned>(n)>safe) || std::find(result.begin(),result.end(),n)!=result.end()) { throw std::invalid_argument("Threads must be unique, in [1,4096], within available CPU/quota limit (or use --allow-oversubscription)"); } result.push_back(n); }
    if(result.empty() || result.size()>64 || text.back()==',') { throw std::invalid_argument("Empty thread count"); }
    if(std::find(result.begin(),result.end(),1)==result.end()) { result.insert(result.begin(),1); } return result;
}
}
