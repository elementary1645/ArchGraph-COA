#include "archgraph/multicore.hpp"
#include "archgraph/analysis.hpp"
#include "archgraph/identity.hpp"
#include "archgraph/perf.hpp"
#include "dynagraph/algorithms/delta_stepping.hpp"
#include "dynagraph/graph/edge_list_io.hpp"
#include <omp.h>
#include <algorithm>
#include <charconv>
#include <chrono>
#include <cmath>
#include <cstdlib>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <tuple>
#include <limits>
#include <map>
#include <set>
#include <sstream>
#include <stdexcept>
#ifdef __linux__
#include <sched.h>
#endif
namespace archgraph::multicore {
namespace {
std::uint64_t next(std::uint64_t& state) {
    auto z=(state+=0x9e3779b97f4a7c15ULL); z=(z^(z>>30))*0xbf58476d1ce4e5b9ULL; z=(z^(z>>27))*0x94d049bb133111ebULL; return z^(z>>31);
}
std::uint64_t bounded(std::uint64_t& state,std::uint64_t bound) { const auto threshold=(0ULL-bound)%bound; for(;;) { auto n=next(state); if(n>=threshold) { return n%bound; } } }
double median(const std::vector<double>& v) { const auto m=v.size()/2; return v.size()%2?v[m]:v[m-1]/2+v[m]/2; }
void numeric(std::ostream& o,std::optional<double> x) { if(x) { o<<*x; } else { o<<"null"; } }
std::string env(const char* key) { const auto* value=std::getenv(key); return value?perf::json_quote(value):"null"; }
struct Runtime {
    int dynamic=omp_get_dynamic(), kind_chunk=0; omp_sched_t kind{};
    Runtime() { omp_get_schedule(&kind,&kind_chunk); omp_set_dynamic(0); }
    ~Runtime() { omp_set_dynamic(dynamic); omp_set_schedule(kind,kind_chunk); }
};
// Every participating worker saves and restores its own affinity, including reused runtime workers.
struct Binding {
    bool requested=false, applied=false, restored=true, changed=false;
#ifdef __linux__
    cpu_set_t* original=nullptr; std::size_t bytes=0;
#endif
    Binding(bool bind,const std::vector<int>& cpus,int worker):requested(bind) {
        if(!bind) { return; }
#ifdef __linux__
        const auto count=static_cast<std::size_t>(cpus.empty()?128:std::max(128,cpus.back()+1)); bytes=CPU_ALLOC_SIZE(count); original=CPU_ALLOC(count);
        if(!original || cpus.empty() || sched_getaffinity(0,bytes,original)!=0) { return; }
        auto* target=CPU_ALLOC(count); if(!target) { return; } CPU_ZERO_S(bytes,target);
        const auto cpu=cpus[static_cast<std::size_t>(worker)%cpus.size()]; CPU_SET_S(static_cast<std::size_t>(cpu),bytes,target);
        if(sched_setaffinity(0,bytes,target)==0) {
            changed=true;
            CPU_ZERO_S(bytes,target); applied=sched_getaffinity(0,bytes,target)==0 && CPU_COUNT_S(bytes,target)==1 && CPU_ISSET_S(static_cast<std::size_t>(cpu),bytes,target);
        } CPU_FREE(target);
#else
        (void)cpus; (void)worker;
#endif
    }
    void restore() {
#ifdef __linux__
        if(original && changed) { restored=sched_setaffinity(0,bytes,original)==0; if(restored) { changed=false; } }
#endif
    }
    ~Binding() { restore();
#ifdef __linux__
        if(original) { CPU_FREE(original); }
#endif
    }
};
struct KernelResult { std::uint64_t checksum=0; int actual=0; bool applied=true,restored=true; double ns=0; };
std::uint64_t item(std::uint64_t value,bool irregular) {
    const auto iterations=irregular?1U+static_cast<unsigned>((value/256)%32)*8U:32U;
    for(unsigned j=0;j<iterations;++j) { value=(value^(value>>27))*0x94d049bb133111ebULL+static_cast<std::uint64_t>(j); }
    return value;
}
KernelResult kernel(const std::vector<std::uint64_t>& data,int threads,int chunk,const std::string& strategy,bool irregular,bool bind,const std::vector<int>& cpus) {
    const auto size=static_cast<std::int64_t>(data.size()); KernelResult r; std::uint64_t sum=0;
    int applied=1,restored=1; std::chrono::steady_clock::time_point begin,end;
    omp_set_schedule(strategy=="dynamic-reduction"?omp_sched_dynamic:omp_sched_static,chunk);
#pragma omp parallel num_threads(threads) shared(sum,r,applied,restored,begin,end)
    {
        Binding binding(bind,cpus,omp_get_thread_num()); const bool was_applied=binding.applied;
        if(bind && !was_applied) {
#pragma omp atomic write
            applied=0;
        }
#pragma omp barrier
#pragma omp single
        { r.actual=omp_get_num_threads(); begin=std::chrono::steady_clock::now(); }
        if(strategy=="static-atomic") {
#pragma omp for schedule(runtime)
            for(std::int64_t i=0;i<size;++i) { const auto value=item(data[static_cast<std::size_t>(i)],irregular);
#pragma omp atomic update
                sum+=value;
            }
        } else if(strategy=="static-critical") {
#pragma omp for schedule(runtime)
            for(std::int64_t i=0;i<size;++i) { const auto value=item(data[static_cast<std::size_t>(i)],irregular);
#pragma omp critical(archgraph_sum)
                { sum+=value; }
            }
        } else {
#pragma omp for schedule(runtime) reduction(+:sum)
            for(std::int64_t i=0;i<size;++i) { sum+=item(data[static_cast<std::size_t>(i)],irregular); }
        }
#pragma omp single
        { end=std::chrono::steady_clock::now(); }
        binding.restore(); if(!binding.restored) {
#pragma omp atomic write
            restored=0;
        }
    }
    r.checksum=sum; r.ns=static_cast<double>(std::chrono::duration_cast<std::chrono::nanoseconds>(end-begin).count()); r.applied=bind && applied; r.restored=restored!=0; return r;
}
struct Options {
    std::string input,threads,affinity="none",csv,workload="uniform",chunks="1,64";
    std::uint64_t seed=1,size=65536,delta=16; unsigned repetitions=15,warmups=1; std::uint32_t source=0;
    double fraction=0.95; bool oversubscribe=false,hardware=false;
};
std::uint64_t number(const std::string& value) {
    std::uint64_t n=0; const auto r=std::from_chars(value.data(),value.data()+value.size(),n);
    if(value.empty() || r.ec!=std::errc{} || r.ptr!=value.data()+value.size()) { throw std::invalid_argument("Expected unsigned decimal integer"); } return n;
}
struct Record { unsigned block; bool warmup; int requested,observed,chunk; std::string strategy; double ns; std::uint64_t checksum; bool affinity_applied,affinity_restored; };
}
std::vector<Slot> schedule(const std::vector<int>& threads,unsigned blocks,unsigned warmups,std::uint64_t seed) {
    if(threads.empty() || blocks<1 || blocks>10000 || warmups>10000) { throw std::invalid_argument("Invalid schedule bounds"); }
    if(threads.size()>64 || threads.size()*(blocks+warmups)>1000000) { throw std::invalid_argument("Schedule exceeds one million trial limit"); }
    std::vector<Slot> result; result.reserve(threads.size()*(blocks+warmups));
    for(unsigned b=0;b<warmups+blocks;++b) {
        auto order=threads; for(std::size_t i=order.size();i>1;--i) { const auto j=static_cast<std::size_t>(bounded(seed,i)); std::swap(order[i-1],order[j]); }
        for(const int p:order) { result.push_back({b<warmups?b:b-warmups,p,b<warmups}); }
    } return result;
}
Summary summarize(std::vector<double> v) {
    if(v.empty() || std::any_of(v.begin(),v.end(),[](double x){return !std::isfinite(x)||x<=0;})) { throw std::invalid_argument("Timings must be finite and positive"); }
    std::sort(v.begin(),v.end()); const auto m=median(v); std::vector<double> deviations; for(double x:v) { deviations.push_back(std::abs(x-m)); } std::sort(deviations.begin(),deviations.end()); return {m,v.front(),v.back(),median(deviations)};
}
std::optional<double> speedup(double b,double t) { if(!std::isfinite(b)||!std::isfinite(t)||b<=0||t<=0||!std::isfinite(b/t)) { return std::nullopt; } return b/t; }
std::optional<double> efficiency(double b,double t,int p) { const auto s=speedup(b,t); return s&&p>0?std::optional<double>(*s/p):std::nullopt; }
std::optional<double> amdahl(double f,int p) { if(!std::isfinite(f)||f<0||f>1||p<1) { return std::nullopt; } return 1/((1-f)+f/p); }
int cli(int argc,char* argv[],std::ostream& out) {
    Options o; const bool scaling=std::string(argv[1])=="scaling"; std::set<std::string> seen;
    for(int i=2;i<argc;++i) {
        const std::string key=argv[i]; if(!seen.insert(key).second) { throw std::invalid_argument("Duplicate option"); }
        if(key=="--allow-oversubscription") { o.oversubscribe=true; continue; }
        if(key=="--hardware-counters") { o.hardware=true; continue; }
        if(i+1==argc) { throw std::invalid_argument("Missing option value"); } const std::string value=argv[++i];
        if(key=="--threads") { o.threads=value; } else if(key=="--affinity") { o.affinity=value; }
        else if(key=="--csv") { o.csv=value; } else if(key=="--seed") { o.seed=number(value); }
        else if(key=="--repetitions" || key=="--warmups") { const auto n=number(value); if(n>10000 || (key=="--repetitions" && n==0)) { throw std::invalid_argument("Invalid trial count"); } if(key=="--repetitions") { o.repetitions=static_cast<unsigned>(n); } else { o.warmups=static_cast<unsigned>(n); } }
        else if(scaling && key=="--input") { o.input=value; } else if(scaling && key=="--source") { const auto n=number(value); if(n>std::numeric_limits<std::uint32_t>::max()) { throw std::invalid_argument("Source out of range"); } o.source=static_cast<std::uint32_t>(n); }
        else if(scaling && key=="--delta") { o.delta=number(value); if(!o.delta) { throw std::invalid_argument("Delta must be positive"); } }
        else if(scaling && key=="--algorithm" && value=="delta-stepping") {}
        else if(scaling && key=="--parallel-fraction") { std::size_t pos=0; o.fraction=std::stod(value,&pos); if(pos!=value.size() || !amdahl(o.fraction,1)) { throw std::invalid_argument("Invalid parallel fraction"); } }
        else if(!scaling && key=="--size") { o.size=number(value); if(o.size<1 || o.size>4194304) { throw std::invalid_argument("Size must be [1,4194304] elements"); } }
        else if(!scaling && key=="--chunks") { o.chunks=value; }
        else if(!scaling && key=="--workload" && (value=="uniform" || value=="irregular")) { o.workload=value; }
        else { throw std::invalid_argument("Unknown or invalid multicore option"); }
    }
    if(o.affinity!="none" && o.affinity!="compact") { throw std::invalid_argument("Affinity must be none or compact"); }
    if(scaling && (o.input.empty() || !seen.count("--source"))) { throw std::invalid_argument("Required: --input and --source"); }
    const auto topology=discover(); const auto metadata=cpu_metadata(); const int original_max=omp_get_max_threads(); Runtime runtime;
    if(o.threads.empty()) { o.threads=topology.safe_threads>=2?"1,2":"1"; }
    const auto threads=parse_threads(o.threads,topology.safe_threads,o.oversubscribe);
    const bool oversubscribed=std::any_of(threads.begin(),threads.end(),[&](int p){return static_cast<unsigned>(p)>topology.safe_threads;});
    if(oversubscribed) { std::cerr<<"Warning: explicit oversubscription; CPU quota/affinity/runtime capacity exceeded\n"; }
    std::vector<Record> records; const auto slots=schedule(threads,o.repetitions,o.warmups,o.seed);
    std::string identity="null"; std::uint64_t vertices=0,edges=0;
    if(scaling) {
        const auto graph=dynagraph::load_edge_list_file(o.input); const auto reference=dynagraph::dijkstra(graph,o.source);
        vertices=graph.vertex_count(); edges=graph.edge_count(); identity=perf::json_quote(graph_identity(graph));
        if(o.affinity=="compact") { throw std::invalid_argument("Compact affinity is supported by parallel-kernels; for scaling use OMP_PLACES and OMP_PROC_BIND and inspect runtime metadata"); }
        for(const auto& slot:slots) {
            int observed=0; const auto begin=std::chrono::steady_clock::now();
            const auto result=dynagraph::delta_stepping(graph,o.source,{o.delta,slot.threads,nullptr,&observed});
            const auto end=std::chrono::steady_clock::now();
            if(result.distances!=reference.distances || result.source!=reference.source) { throw std::runtime_error("SSSP correctness mismatch"); }
            std::uint64_t checksum=0; for(auto d:result.distances) { checksum+=d; }
            records.push_back({slot.block,slot.warmup,slot.threads,observed,0,"delta-stepping",static_cast<double>(std::chrono::duration_cast<std::chrono::nanoseconds>(end-begin).count()),checksum,false,true});
        }
    } else {
        (void)parse_threads(o.chunks,4096,true); std::vector<int> granularities; std::istringstream c(o.chunks); std::string value;
        while(std::getline(c,value,',')) { granularities.push_back(static_cast<int>(number(value))); }
        std::vector<std::uint64_t> data(static_cast<std::size_t>(o.size)); std::uint64_t expected=0;
        for(std::size_t i=0;i<data.size();++i) { data[i]=static_cast<std::uint64_t>(i)^o.seed; expected+=item(data[i],o.workload=="irregular"); }
        struct Config { int p,chunk; std::string strategy; }; std::vector<Config> configs;
        for(int p:threads) { for(int chunk:granularities) { for(const auto* strategy:{"static-reduction","dynamic-reduction","static-atomic","static-critical"}) { configs.push_back({p,chunk,strategy}); } } }
        if(configs.size()*(o.warmups+o.repetitions)>1000000) { throw std::invalid_argument("Kernel schedule exceeds one million trial limit"); }
        auto seed=o.seed;
        for(unsigned block=0;block<o.warmups+o.repetitions;++block) {
            auto order=configs; for(std::size_t i=order.size();i>1;--i) { std::swap(order[i-1],order[static_cast<std::size_t>(bounded(seed,i))]); }
            for(const auto& config:order) {
                const auto r=kernel(data,config.p,config.chunk,config.strategy,o.workload=="irregular",o.affinity=="compact",topology.available_cpus);
                if(r.checksum!=expected) { throw std::runtime_error("Kernel checksum mismatch"); }
                records.push_back({block<o.warmups?block:block-o.warmups,block<o.warmups,config.p,r.actual,config.chunk,config.strategy,r.ns,r.checksum,r.applied,r.restored});
            }
        }
    }
    using Key=std::tuple<std::string,int,int>; std::map<Key,std::vector<double>> times;
    for(const auto& r:records) {
        if(!std::isfinite(r.ns) || r.ns<=0) { throw std::runtime_error("Trial clock duration must be finite and positive"); }
        if(!r.warmup) { times[{r.strategy,r.chunk,r.requested}].push_back(r.ns); }
    }
    std::map<Key,Summary> summaries; for(const auto& entry:times) { summaries.emplace(entry.first,summarize(entry.second)); }
    std::ostringstream json; json<<std::setprecision(17)<<"{\"schema\":\"archgraph-multicore-experiments\",\"schema_version\":1,\"experiment_type\":"<<perf::json_quote(scaling?"scaling":"parallel-kernels")
        <<",\"status\":\"completed\",\"verified\":true,\"algorithm\":"<<perf::json_quote(scaling?"delta-stepping":"checksum-transform")
        <<",\"graph_provenance\":{\"path\":"<<(scaling?perf::json_quote(o.input):"null")<<",\"identity_method\":\"fnv1a64-csr-le-u64-v1\",\"identity\":"<<identity<<",\"vertices\":"<<vertices<<",\"edges\":"<<edges<<"}"
        <<",\"source\":"<<o.source<<",\"delta\":"<<o.delta<<",\"size_elements\":"<<o.size<<",\"workload\":"<<perf::json_quote(o.workload)
        <<",\"seed\":"<<o.seed<<",\"repetitions\":"<<o.repetitions<<",\"warmups\":"<<o.warmups
        <<",\"trial_order\":\"seeded SplitMix64 Fisher-Yates; complete randomized blocks; warmup blocks first\",\"metadata\":"<<metadata<<",\"topology\":"<<topology_json(topology)
        <<",\"runtime\":{\"openmp_available\":true,\"max_threads_before_experiment\":"<<original_max<<",\"thread_limit\":"<<omp_get_thread_limit()<<",\"dynamic_during_experiment\":false,\"dynamic_before\":"<<(runtime.dynamic?"true":"false")<<",\"omp_places\":"<<env("OMP_PLACES")<<",\"omp_proc_bind\":"<<env("OMP_PROC_BIND")<<",\"omp_num_threads\":"<<env("OMP_NUM_THREADS")<<",\"omp_dynamic\":"<<env("OMP_DYNAMIC")<<",\"omp_thread_limit\":"<<env("OMP_THREAD_LIMIT")<<",\"omp_wait_policy\":"<<env("OMP_WAIT_POLICY")<<",\"runtime_library_version\":null}"
        <<",\"measurement_scope\":"<<perf::json_quote(scaling?"complete public algorithm call including allocations and team startup":"worksharing kernel plus barriers; excludes allocation, team startup and affinity setup")
        <<",\"affinity\":{\"requested\":"<<perf::json_quote(o.affinity)<<",\"scope\":\"per worker; kernel binding outside timing; restored after each trial\"}"
        <<",\"baseline_definition\":"<<perf::json_quote(scaling?"median one-thread delta-stepping; Dijkstra only correctness oracle":"median one-thread identical strategy/chunk/workload")
        <<",\"efficiency_denominator\":\"requested_threads; ratios null if observed teams differ from requests\",\"amdahl\":{\"theoretical\":true,\"assumed_parallel_fraction\":"<<o.fraction<<"}"
        <<",\"counter_status\":"<<perf::json_quote(o.hardware?"unsupported_scope":"not_requested")<<",\"counters\":"<<perf::counters_json(perf::unavailable(o.hardware?"unsupported_scope":"not_requested","OpenMP worker aggregation is not implemented"))
        <<",\"oversubscribed\":"<<(oversubscribed?"true":"false")<<",\"environment_limitations\":[\"Shared-host timings are descriptive; no controlled scaling or statistical significance claim\",\"No dedicated cores, fixed frequency, NUMA placement or cold-cache guarantee\"],\"trials\":[";
    for(std::size_t i=0;i<records.size();++i) { const auto& r=records[i]; if(i) { json<<','; } json<<"{\"block\":"<<r.block<<",\"warmup\":"<<(r.warmup?"true":"false")<<",\"requested_threads\":"<<r.requested<<",\"observed_threads\":"<<r.observed<<",\"strategy\":"<<perf::json_quote(r.strategy)<<",\"chunk\":"<<r.chunk<<",\"wall_ns\":"<<r.ns<<",\"checksum\":"<<r.checksum<<",\"affinity_applied\":"<<(r.affinity_applied?"true":"false")<<",\"affinity_restored\":"<<(r.affinity_restored?"true":"false")<<'}'; }
    json<<"],\"summaries\":["; bool first=true;
    for(const auto& entry:summaries) {
        if(!first) { json<<','; } first=false; const auto& strategy=std::get<0>(entry.first); const int chunk=std::get<1>(entry.first),p=std::get<2>(entry.first); const auto& s=entry.second;
        const auto baseline=summaries.at({strategy,chunk,1}).median;
        bool valid=true; for(const auto& r:records) { if(!r.warmup && r.strategy==strategy && r.chunk==chunk && (r.requested==1 || r.requested==p) && r.observed!=r.requested) { valid=false; } }
        json<<"{\"strategy\":"<<perf::json_quote(strategy)<<",\"chunk\":"<<chunk<<",\"requested_threads\":"<<p<<",\"median_wall_ns\":"<<s.median<<",\"minimum_wall_ns\":"<<s.minimum<<",\"maximum_wall_ns\":"<<s.maximum<<",\"mad_wall_ns\":"<<s.mad<<",\"speedup\":"; numeric(json,valid?speedup(baseline,s.median):std::nullopt);
        json<<",\"efficiency\":"; numeric(json,valid?efficiency(baseline,s.median,p):std::nullopt); json<<",\"amdahl_speedup\":"; numeric(json,amdahl(o.fraction,p)); json<<'}';
    } json<<"]}\n";
    if(!o.csv.empty()) {
        std::ofstream csv(o.csv); if(!csv) { throw std::runtime_error("Cannot open CSV"); }
        csv<<"schema_version,block,warmup,strategy,chunk,requested_threads,observed_threads,wall_ns,checksum,affinity_applied,affinity_restored\n"<<std::setprecision(17);
        for(const auto& r:records) { csv<<"1,"<<r.block<<','<<r.warmup<<','<<r.strategy<<','<<r.chunk<<','<<r.requested<<','<<r.observed<<','<<r.ns<<','<<r.checksum<<','<<r.affinity_applied<<','<<r.affinity_restored<<'\n'; } csv.close(); if(!csv) { throw std::runtime_error("CSV write failed"); }
    }
    out<<json.str(); return out?0:2;
}
}
