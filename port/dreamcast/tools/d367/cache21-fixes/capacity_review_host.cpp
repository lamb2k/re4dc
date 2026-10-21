// Extend the frozen capacity fixture. Actual candidate runtime remains unchanged.
#define main frozen_capacity_main
#include "motion_capacity_host.cpp"
#undef main

static unsigned invalid_sdk_frees;
static std::function<void()> before_heap_destroy;
extern "C" void __real_OSFreeToHeap(int, void*);
extern "C" void __wrap_OSFreeToHeap(int heap, void* p)
{
    if (heap >= 0 && HeapHead[heap].size < 0) ++invalid_sdk_frees;
    __real_OSFreeToHeap(heap, p);
}
extern "C" void __real_OSDestroyHeap(int);
extern "C" void __wrap_OSDestroyHeap(int heap)
{
    if (before_heap_destroy) before_heap_destroy();
    __real_OSDestroyHeap(heap);
}
static OSHeapDescriptor heap_backup[13];
Re4dcMemLayout re4dc_mem{};
#include "capacity_actual_review.inc"

static void warm(Binding& b)
{
    for (unsigned i = 0; i < 3; ++i) {
        const int token = acquire_entry(b, i);
        re4dc_motion_release(token);
    }
    assert(overflow_count() == 1);
}
static void raw_sr_contract()
{
    reset();
    unsigned accepted = 0, rejected = 0;
    for (unsigned mask = 0; mask <= 0xf0; mask += 0x10) {
        host_irq_sr = 0x40000001 | mask;
        const bool allowed = can_wait_required();
        assert(host_irq_sr == (0x40000001 | mask) && !host_irq_depth);
        assert(allowed == (CAPACITY_CONTEXT_GUARD_EXPECT ? mask == 0 : mask != 0xf0));
        if (allowed) ++accepted; else ++rejected;
    }
    host_irq_sr = 0x40000001; host_inside_interrupt = true;
    assert(!can_wait_required()); host_inside_interrupt = false;
    host_irq_sr = 0;
    for (unsigned state : {0x10000000U, 0x20000000U, 0x30000000U}) {
        host_irq_sr = 0x40000001 | state;
        assert(can_wait_required() == !CAPACITY_CONTEXT_GUARD_EXPECT);
        assert(host_irq_sr == (0x40000001 | state));
    }
    host_irq_sr = 0;
    host_thread_present = false;
    assert(!can_wait_required());
#if CAPACITY_CONTEXT_GUARD_EXPECT
    host_pass_calls = 0;
    assert(!re4dc_motion_required_alloc(Heap[4].handle, 32));
    assert(!host_pass_calls);
#endif
    host_thread_present = true;
    std::cout << "raw SR predicate: guard=" << CAPACITY_CONTEXT_GUARD_EXPECT
              << " allowed=" << accepted << " rejected=" << rejected
              << "; BL/RB/ISR/no-thread controls and exact prior SR restore PASS\n";

    for (unsigned mask : {0U, 0x10U, 0x80U, 0xe0U, 0xf0U, 0x10000000U, 0x20000000U, 0x30000000U}) {
        reset(); {
            ActualArchive a({22400, 32416, 17408}); assert(a.bind());
            auto& b = bindings[0]; void* trim = trim_free(83168);
            std::promise<void> pinned; auto ready = pinned.get_future();
            std::atomic<bool> finish{false};
            std::thread borrower([&] {
                std::vector<int> tokens;
                for (unsigned i = 0; i < 3; ++i) tokens.push_back(acquire_entry(b, i));
                pinned.set_value();
                while (!finish) std::this_thread::yield();
                for (int token : tokens) re4dc_motion_release(token);
            });
            ready.get(); assert(overflow_count() == 1);
            void* fill = trim_free(64); host_masked_yields = host_pass_calls = 0;
            host_irq_sr = 0x40000001 | mask;
            host_inside_interrupt = mask == 0; // explicit ISR even with unmasked prior SR
            bool yielded = false;
            try {
                assert(!re4dc_motion_required_alloc(Heap[4].handle, 17408));
            } catch (const std::runtime_error& e) {
                yielded = std::string(e.what()) == "masked yield observer";
                assert(yielded);
            }
            const bool refused = CAPACITY_CONTEXT_GUARD_EXPECT || mask == 0xf0 || host_inside_interrupt;
            assert(yielded == !refused);
            assert(host_masked_yields == (refused ? 0U : 1U));
            assert(host_pass_calls == (refused ? 0U : 1U));
            assert(!required_waiters && host_irq_sr == (0x40000001 | mask));
            host_masked_yields = host_pass_calls = 0; bool retire_yielded = false;
            try { assert(!re4dc_motion_capacity_retire()); }
            catch (const std::runtime_error& e) {
                retire_yielded = std::string(e.what()) == "masked yield observer";
                assert(retire_yielded);
            }
            assert(retire_yielded == !refused && host_pass_calls == (refused ? 0U : 1U));
            assert(!required_waiters && host_irq_sr == (0x40000001 | mask));
            host_irq_sr = 0; host_inside_interrupt = false; finish = true; borrower.join();
            OSFreeToHeap(Heap[4].handle, fill); OSFreeToHeap(Heap[4].handle, trim); valid_heap();
        }
    }
    reset(); {
        ActualArchive a({22400, 32416, 17408}); assert(a.bind()); auto& b = bindings[0];
        void* trim = trim_free(83168); std::vector<int> tokens;
        for (unsigned i = 0; i < 3; ++i) tokens.push_back(acquire_entry(b, i));
        void* fill = trim_free(64); host_irq_sr = 0x40000001; host_pass_calls = 0;
        assert(!re4dc_motion_required_alloc(Heap[4].handle, 17408));
        assert(!re4dc_motion_capacity_retire() && !host_pass_calls && host_irq_sr == 0x40000001);
        host_irq_sr = 0;
        for (int token : tokens) re4dc_motion_release(token);
        OSFreeToHeap(Heap[4].handle, fill); OSFreeToHeap(Heap[4].handle, trim); valid_heap();
    }
    std::cout << "actual required requests: guard=" << CAPACITY_CONTEXT_GUARD_EXPECT
              << "; all IMASK/BL/RB contexts restore exact SR; refused contexts never call thd_pass PASS\n";
}

static void static_preflight_and_high_placement()
{
    reset(); re4dc_mem.heap = reinterpret_cast<std::uintptr_t>(arena); room4 = {true, 1, 0, 0, 0, 0}; {
        ActualArchive a({22400, 32416, 17408}); assert(a.bind());
        auto& b = bindings[0]; void* trim = trim_free(83168); warm(b);
        const unsigned before = re4dc_static_heap_free(), evictions = stats.evictions;
        assert(before == 65664 && !re4dc_static_alloc(1024));
        assert(re4dc_static_heap_free() == int(before) && overflow_count() == 1 && stats.evictions == evictions);
        assert(re4dc_motion_capacity_retire());
        assert(re4dc_static_heap_free() == 83168 && !overflow_count());
        void* native = re4dc_static_alloc(1024); assert(native);
        room_free4(native, "review preflight"); OSFreeToHeap(Heap[4].handle, trim); valid_heap();
    }
    std::cout << "actual static preflight:1024B rejected at65664B, no reclaim; explicit overflow drain restores83168B and same request succeeds PASS\n";

    reset(); re4dc_mem.heap = reinterpret_cast<std::uintptr_t>(arena); room4 = {true, 2, 0, 0, 0, 0}; {
        ActualArchive a({22400, 32416, 17408}); assert(a.bind());
        auto& b = bindings[0]; void* trim = trim_free(83168); warm(b);
        OSFreeToHeap(Heap[4].handle, trim);
        void* first = mem_alloc(128000, nullptr, 0, 0, 4); assert(first);
        void* barrier1 = mem_alloc(64, nullptr, 0, 0, 4); assert(barrier1);
        void* second = mem_alloc(128000, nullptr, 0, 0, 4); assert(second);
        void* barrier2 = mem_alloc(64, nullptr, 0, 0, 4); assert(barrier2);
        OSFreeToHeap(Heap[4].handle, first); OSFreeToHeap(Heap[4].handle, second);
        unsigned total = 0; const unsigned largest = re4dc_heap_largest_current(&total);
        const unsigned request = largest + 8192;
        assert(total >= request + kSourceReserve + kAllocationOverhead + sizeof(Room4Cell));
        const unsigned evictions = stats.evictions;
        assert(!re4dc_static_alloc(request));
        assert(overflow_count() == 1 && stats.evictions == evictions);
        assert(re4dc_motion_capacity_retire());
        void* native = re4dc_static_alloc(request); assert(native);
        room_free4(native, "review high allocation");
        OSFreeToHeap(Heap[4].handle, barrier1); OSFreeToHeap(Heap[4].handle, barrier2); valid_heap();
        std::cout << "actual high placement: request=" << request << " total=" << total << " largest=" << largest
                  << " fails without reclaim, succeeds after explicit overflow drain PASS\n";
    }
}

static void held_reset_and_remaining_native_owners()
{
    reset(); invalid_sdk_frees = 0; {
        ActualArchive a({22400, 32416, 17408}); assert(a.bind()); warm(bindings[0]);
        re4dc_motion_hold(1); bool refused = false;
        try { MemClearAllHeap(); } catch (const Missing& e) {
            refused = std::string(e.what()) == "motion overflow reader before all-heap clear";
        }
        assert(refused && Heap[4].handle >= 0 && stats.metadata_bytes && !invalid_sdk_frees);
        re4dc_motion_forget_dead_heaps();
        MemClearAllHeap();
        assert(Heap[4].handle == -1 && stats.metadata_bytes && bindings[0].archive && capacity_retiring);
    }
    assert(invalid_sdk_frees >= 2);
    std::cout << "actual MemClearAllHeap: held reset explicitly refuses before destroy; unheld retire leaves metadata/reserve alive, later native frees after SDK destruction="
              << invalid_sdk_frees << " PASS (generic reset defect persists)\n";
}

static void retirement_admission_interleaving()
{
    reset(); invalid_sdk_frees = 0; bool reopened = false; {
        ActualArchive first({22400, 32416, 17408}), newcomer({12032, 7744, 12224});
        assert(first.bind()); warm(bindings[0]);
        before_heap_destroy = [&] {
            assert(capacity_retiring && Heap[4].handle >= 0);
            assert(newcomer.bind());
            reopened = !capacity_retiring;
        };
        // Deterministic boundary interleaving, not a claimed gameplay callback.
        MemClearAllHeap(); before_heap_destroy = nullptr;
        assert(reopened && Heap[4].handle == -1 && stats.metadata_bytes);
    }
    assert(invalid_sdk_frees >= 4);
    std::cout << "actual retire-to-destroy boundary: a new bind clears capacity_retiring before SDK destruction; native frees later="
              << invalid_sdk_frees << " PASS (external admission serialization required; injected interleaving)\n";
}

int main()
{
    // Retain the original candidate's exact-size, pin, lock, concurrency,
    // fragmentation, cap, failure, hold and unsupported-full-mask controls.
    k05_sequential();
    k05_coactive_and_required_pin_wait();
    required_lock_busy_read();
    concurrent_required_allocators();
    binding_admission_reclaims_without_recursion();
    fragmentation_and_original_failure();
    aggregate_cap_and_pins();
    failed_read_hold_strict_and_retire();
#if RE4DC_MOTION_RESUME
    movie_loans_keep_owner_tickets();
#endif
    unsupported_contexts_do_not_deadlock();
    raw_sr_contract();
    static_preflight_and_high_placement();
    held_reset_and_remaining_native_owners();
    retirement_admission_interleaving();
}
