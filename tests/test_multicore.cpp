#include "archgraph/multicore.hpp"
#include "test_support.hpp"
#include <cmath>
#include <filesystem>
#include <fstream>
#include <limits>
#include <set>
#include <sstream>
#include <omp.h>
#ifdef __linux__
#include <sched.h>
#endif
using namespace archgraph::multicore;
using dynagraph::test::require;
using dynagraph::test::require_throws;
int main() { return dynagraph::test::run("multicore",[] {
    require(parse_cpu_list("1,4-6,10\n")==std::vector<int>({1,4,5,6,10}),"sparse CPUs");
    for(const auto* bad:{"","-1","2-1","1,","a","1--2"}) { require_throws<std::invalid_argument>([&]{(void)parse_cpu_list(bad);},""); }
    require(parse_quota("150000 100000")==1.5,"v2 quota"); require(parse_quota("50000","100000")==0.5,"v1 quota");
    require(!parse_quota("max 100000") && !parse_quota("-1","100000"),"unlimited");
    for(const auto* bad:{"0 100","1 0","garbage","-2 100","1 100 trailing"}) { require_throws<std::invalid_argument>([&]{(void)parse_quota(bad);},""); }
    require(parse_threads("2",2,false)==std::vector<int>({1,2}),"baseline inserted");
    for(const auto* bad:{"0","-1","1,1","1,","3","4097"}) { require_throws<std::invalid_argument>([&]{(void)parse_threads(bad,2,false);},""); }
    require(parse_threads("1,3",2,true).size()==2,"explicit oversubscription");
    const auto a=schedule({1,2,4},7,2,99), b=schedule({1,2,4},7,2,99),c=schedule({1,2,4},7,2,100);
    require(a.size()==27,"complete blocks"); bool different=false;
    for(std::size_t i=0;i<a.size();++i) { require(a[i].threads==b[i].threads && a[i].block==b[i].block && a[i].warmup==b[i].warmup,"repeat schedule"); different|=a[i].threads!=c[i].threads; }
    require(different,"seed changes order");
    for(std::size_t i=0;i<a.size();i+=3) { std::set<int> values; for(std::size_t j=0;j<3;++j) { values.insert(a[i+j].threads); } require(values.size()==3,"balanced block"); }
    const auto s=summarize({1,2,4,10}); require(s.median==3 && s.minimum==1 && s.maximum==10 && s.mad==1.5,"summary arithmetic");
    require(speedup(100,25)==4 && efficiency(100,25,8)==0.5,"scaling arithmetic"); require(std::abs(*amdahl(0.9,4)-1/0.325)<1e-12,"Amdahl");
    require(amdahl(0,8)==1 && amdahl(1,8)==8 && !amdahl(1.1,2) && !amdahl(0.5,0),"Amdahl boundaries");
    for(double x:{0.0,-1.0,std::numeric_limits<double>::infinity(),std::numeric_limits<double>::quiet_NaN()}) { require(!speedup(x,1)&&!speedup(1,x),"invalid ratio"); require_throws<std::invalid_argument>([&]{(void)summarize({x});},""); }
    require(!efficiency(1,1,0),"invalid threads");
    const auto root=std::filesystem::current_path()/"archgraph-topology-unit"; std::filesystem::remove_all(root);
    const auto write=[&](const std::string& path,const std::string& text) { const auto p=root/path; std::filesystem::create_directories(p.parent_path()); std::ofstream(p)<<text; };
    write("proc/self/status","Cpus_allowed_list:\t2,6\n"); write("proc/self/cgroup","0::/child\n"); write("sys/devices/system/cpu/online","0-7\n");
    for(int cpu:{2,6}) { const auto base="sys/devices/system/cpu/cpu"+std::to_string(cpu)+"/topology/"; write(base+"core_id","1"); write(base+"physical_package_id","0"); write(base+"thread_siblings_list","2,6"); }
    write("sys/fs/cgroup/child/cpu.max","200000 100000"); write("sys/fs/cgroup/cpu.max","50000 100000");
    const auto t=discover((root/"sys").string(),(root/"proc").string()); require(t.available_cpus==std::vector<int>({2,6}) && t.physical_cores==1 && t.sockets==1 && t.smt==true,"topology"); require(t.quota_cpus==0.5 && t.safe_threads==1,"ancestor quota");
    write("sys/fs/cgroup/child/cpu.max","max 100000"); write("sys/fs/cgroup/cpu.max","max 100000");
    require(discover((root/"sys").string(),(root/"proc").string()).safe_threads==2,"unlimited quota");
    std::filesystem::remove_all(root);
    write("proc/self/status","Cpus_allowed_list: 2,6\n"); write("proc/self/cgroup","2:cpu,cpuacct:/nested\n");
    write("sys/fs/cgroup/cpu/nested/cpu.cfs_quota_us","100000"); write("sys/fs/cgroup/cpu/nested/cpu.cfs_period_us","100000");
    const auto v1=discover((root/"sys").string(),(root/"proc").string()); require(v1.quota_cpus==1 && v1.safe_threads==1 && !v1.physical_cores,"v1 and missing topology");
    std::filesystem::remove_all(root);
    omp_set_dynamic(1); omp_set_schedule(omp_sched_dynamic,17);
#ifdef __linux__
    cpu_set_t before{},after{}; const bool mask_known=sched_getaffinity(0,sizeof(before),&before)==0;
#endif
    std::vector<std::string> args={"archgraph","parallel-kernels","--threads","1","--size","17","--chunks","2","--repetitions","1","--warmups","0","--affinity","compact"};
    std::vector<char*> argv; for(auto& arg:args) { argv.push_back(arg.data()); } std::ostringstream output;
    require(cli(static_cast<int>(argv.size()),argv.data(),output)==0,"in-process kernel");
    omp_sched_t kind{}; int chunk=0; omp_get_schedule(&kind,&chunk);
    require(omp_get_dynamic()!=0 && kind==omp_sched_dynamic && chunk==17,"runtime configuration restored");
#ifdef __linux__
    if(mask_known) { require(sched_getaffinity(0,sizeof(after),&after)==0 && CPU_EQUAL(&before,&after),"caller affinity restored"); }
#endif
    omp_set_dynamic(0);
}); }
