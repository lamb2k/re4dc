#pragma once
// Synthetic KOS/services for complete production-TU execution. No target ABI,
// scheduler, network stack or hardware timing claim is made by these adapters.
#include <algorithm>
#include <cassert>
#include <climits>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <cstdarg>
#include <deque>
#include <string>
#include <vector>
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <fcntl.h>
#include <unistd.h>

using tid_t = int;
using irq_mask_t = unsigned;
enum { STATE_ZOMBIE, STATE_FINISHED, STATE_READY, STATE_RUNNING };
struct kthread_t { int id; int state = STATE_READY; };
struct kthread_attr_t {
    bool create_detached;
    unsigned stack_size;
    void* stack_ptr;
    int prio;
    const char* label;
    bool disable_tls;
};
struct kthread_worker_t { kthread_t* thread; };
struct netif_t { unsigned char ip_addr[4]; };
enum { PRIO_DEFAULT = 10, PPP_PHASE_DEAD = 1 };

namespace fixture {
struct Packet { std::string bytes; unsigned addr; unsigned short port; int family = AF_INET; };
inline std::vector<std::string> calls, sent;
inline std::deque<Packet> incoming;
inline unsigned sent_addr, heap_free = 65536, heap_break;
inline uint64_t now_ms;
inline bool connected = true, thread_ok = true;
inline int write_result = -1, ppp_init_result, modem_init_result, login_result, connect_result;
inline int socket_result = 7, bind_result, fcntl_result;
inline unsigned driver_calls, slept, phase_calls, destroy_calls, login_clears;
inline unsigned irq_depth, irq_queries;
inline kthread_t threads[8] = {{1}, {2}, {3}, {4}, {5}, {6}, {7}, {8}};
inline kthread_t* current = &threads[0];
inline kthread_attr_t last_attr{};
inline void* (*created_entry)(void*);
inline void* created_arg;
inline void (*sleep_hook)(unsigned), (*shutdown_hook)(), (*send_hook)();
inline netif_t net = {{192, 0, 2, 2}};
inline void note(const char* s) { calls.emplace_back(s); }
inline unsigned count(const char* s) { return std::count(calls.begin(), calls.end(), s); }
inline void reset() {
    calls.clear(); sent.clear(); incoming.clear(); sent_addr = 0;
    heap_free = 65536; heap_break = 0; now_ms = 0;
    connected = true; thread_ok = true; write_result = -1;
    ppp_init_result = modem_init_result = login_result = connect_result = 0;
    socket_result = 7; bind_result = fcntl_result = 0;
    driver_calls = slept = phase_calls = destroy_calls = login_clears = 0;
    irq_depth = irq_queries = 0;
    for (auto& t : threads) t.state = STATE_READY;
    current = &threads[0]; last_attr = {}; created_entry = nullptr; created_arg = nullptr;
    sleep_hook = nullptr; shutdown_hook = nullptr; send_hook = nullptr;
}
inline unsigned address(const char* s) { return inet_addr(s); }
}

inline netif_t* net_default_dev = &fixture::net;
extern "C" {
inline kthread_t* thd_get_current() { return fixture::current; }
inline tid_t thd_get_id(const kthread_t* t) { return t->id; }
inline kthread_t* thd_by_tid(tid_t id) {
    assert(fixture::irq_depth); ++fixture::irq_queries;
    for (auto& t : fixture::threads) if (t.id == id) return &t;
    return nullptr;
}
inline irq_mask_t irq_disable() { return fixture::irq_depth++; }
inline void irq_restore(irq_mask_t state) { fixture::irq_depth = state; }
inline int thd_get_prio(kthread_t*) { return 10; }
inline kthread_t* thd_create_ex(const kthread_attr_t* a, void* (*fn)(void*), void* arg) {
    assert(!fixture::irq_depth);   // no new long masked interval around creation
    fixture::note("thread.create"); fixture::last_attr = *a;
    fixture::created_entry = fn; fixture::created_arg = arg;
    return fixture::thread_ok ? &fixture::threads[1] : nullptr;
}
inline void thd_sleep(unsigned ms) {
    fixture::now_ms += ms; fixture::slept += ms;
    if (fixture::sleep_hook) fixture::sleep_hook(ms);
}
inline void thd_destroy(kthread_t*) { ++fixture::destroy_calls; fixture::note("thread.destroy"); }
inline kthread_t* thd_worker_get_thread(kthread_worker_t* w) { return w->thread; }
inline uint64_t timer_ms_gettime64() { return fixture::now_ms; }
inline uint64_t timer_us_gettime64() { return fixture::now_ms * 1000; }
inline int modem_is_connected() { return fixture::connected; }
inline int modem_write_data(unsigned char*, int size) {
    ++fixture::driver_calls; fixture::note("modem.write");
    return fixture::write_result < 0 ? size : std::min(size, fixture::write_result);
}
inline int modem_read_data(unsigned char*, int) { fixture::note("modem.read"); return 0; }
inline void modem_shutdown() {
    fixture::note("modem.shutdown");
    // Deliberately retain connected: pinned KOS shutdown does not clear its flag.
    if (fixture::shutdown_hook) fixture::shutdown_hook();
}
inline int ppp_init() { fixture::note("ppp.init"); return fixture::ppp_init_result; }
inline int ppp_modem_init(const char*, int, int* rate) {
    fixture::note("modem.init"); *rate = 33600; return fixture::modem_init_result;
}
inline int ppp_set_login(const char* name, const char* pass) {
    assert((name == nullptr) == (pass == nullptr));
    if (!name) { ++fixture::login_clears; fixture::note("login.clear"); return 0; }
    fixture::note("login.set"); return fixture::login_result;
}
inline int ppp_connect() { fixture::note("ppp.connect"); return fixture::connect_result; }
inline int ppp_shutdown() { fixture::note("ppp.shutdown"); return 0; }
inline int fs_socket_init() { fixture::note("socket.init"); return 0; }
inline int net_udp_init() { fixture::note("udp.init"); return 0; }
inline int _ppp_enter_phase(int phase) {
    assert(phase == PPP_PHASE_DEAD); ++fixture::phase_calls;
    fixture::note("phase.dead"); return 0;
}
inline void modemIntShutdown() { fixture::note("timer.down"); }
inline void re4dc_log(const char*, ...) { fixture::note("log"); }
inline void re4dc_kos_heap_state(unsigned* f, unsigned* u, unsigned* b) {
    fixture::note("heap.read"); *f = fixture::heap_free; *u = 0; *b = fixture::heap_break;
}
inline int fixture_socket(int, int, int) { fixture::note("socket.open"); return fixture::socket_result; }
inline int fixture_bind(int, const sockaddr*, socklen_t) { fixture::note("socket.bind"); return fixture::bind_result; }
inline int fixture_fcntl(int, int, ...) { fixture::note("socket.nonblock"); return fixture::fcntl_result; }
inline int fixture_close(int) { fixture::note("socket.close"); return 0; }
inline ssize_t fixture_recvfrom(int, void* p, size_t max, int, sockaddr* from, socklen_t* fl) {
    fixture::note("socket.recv");
    if (fixture::incoming.empty()) return -1;
    const auto packet = fixture::incoming.front(); fixture::incoming.pop_front();
    sockaddr_in a{}; a.sin_family = packet.family;
    a.sin_addr.s_addr = packet.addr; a.sin_port = htons(packet.port);
    std::memcpy(from, &a, std::min<size_t>(*fl, sizeof(a))); *fl = sizeof(a);
    const size_t n = std::min(max, packet.bytes.size());
    std::memcpy(p, packet.bytes.data(), n); return n;
}
inline ssize_t fixture_sendto(int, const void* p, size_t n, int, const sockaddr* to, socklen_t) {
    fixture::note("socket.send"); fixture::sent.emplace_back((const char*) p, n);
    fixture::sent_addr = ((const sockaddr_in*) to)->sin_addr.s_addr;
    if (fixture::send_hook) fixture::send_hook();
    return n;
}
}

#define socket fixture_socket
#define bind fixture_bind
#define fcntl fixture_fcntl
#define close fixture_close
#define recvfrom fixture_recvfrom
#define sendto fixture_sendto
