// Extends the pinned H064 fixture's host projections, not its runtime decisions.
#include <array>
#include <cstdlib>
#include <vector>
static std::vector<void*> debug_frees, table_allocations;
static unsigned transport_reads, publication_observations;
static void host_before_clear(void*, unsigned);
static void Debug_free(void* p) { debug_frees.push_back(p); }
static int HDReadDebugAlloc(char*, void**, int) { ++transport_reads; return 0; }
static void* host_table_alloc(unsigned n, int, int) {
    void* p = std::malloc(n ? n : 1); table_allocations.push_back(p); return p;
}
static void Mem_free(void* p) {
    for (auto& allocation : table_allocations) if (allocation == p) {
        allocation = nullptr; std::free(p); return;
    }
    std::abort();
}
#define MEM_ALLOC host_table_alloc
#define main h064_original_main
#include "h064_event_admission_adapted.cpp"
#undef main

static EventMgr* observed;
static const char* observed_name;
static void host_before_clear(void* p, unsigned) {
    if (!observed) return;
    const auto address = reinterpret_cast<std::uintptr_t>(p);
    const auto begin = reinterpret_cast<std::uintptr_t>(observed->BinTbl.pWork);
    const auto end = begin + observed->BinTbl.NumDatTbl * sizeof(DatTblEntry);
    if (address >= begin && address < end) {
        assert(observed->EvdTbl.ChkDat(observed_name) == 0);
        ++publication_observations;
    }
}

static unsigned cases;
static unsigned char* arena;
static char parent_name[] = "synthetic.evd";
static EvtHeader* header(unsigned offset, unsigned count) {
    auto* hdr = event_at(arena + offset); // H064's exact header constructor.
    hdr->nBin = count;
    auto* entries = reinterpret_cast<EvtBinEntry*>(reinterpret_cast<u8*>(hdr) + hdr->binOfs);
    for (unsigned i = 0; i < count; ++i) {
        std::memset(&entries[i], 0, sizeof(entries[i]));
        std::snprintf(entries[i].name, sizeof(entries[i].name), "part%03u.bin", i);
        entries[i].ofs = 32768 + i * 32;
    }
    return hdr;
}
static EvtBinEntry* parts(EvtHeader* hdr) {
    return reinterpret_cast<EvtBinEntry*>(reinterpret_cast<u8*>(hdr) + hdr->binOfs);
}
struct Fixture {
    std::array<DatTblEntry, 32> parents{};
    std::array<DatTblEntry, 320> bins{};
    EventMgr manager{{32, parents.data()}, {320, bins.data()}};
    EvtHeader* hdr = header(0, 4);
    Fixture() { errors = transport_reads = 0; debug_frees.clear(); ++cases; }
    void observe() { observed = &manager; observed_name = parent_name; }
    void stop_observing() { observed = nullptr; observed_name = nullptr; }
    ~Fixture() { stop_observing(); }
    int admit(int flag = 0, void* dat2 = nullptr) {
        return manager.SetEvd(parent_name, hdr, dat2, flag);
    }
    void complete() {
        assert(manager.EvdTbl.ChkDat(parent_name) == 1);
        for (int i = 0; i < hdr->nBin; ++i) assert(manager.BinTbl.ChkDat(parts(hdr)[i].name) == 1);
    }
};
template <std::size_t N> static bool identical(const std::array<DatTblEntry, N>& a,
                                             const std::array<DatTblEntry, N>& b) {
    return std::memcmp(a.data(), b.data(), sizeof(a)) == 0;
}

static void failures_and_retry() {
    // A real capacity refusal at every child, then the parent commit.
    for (int flag : {0, 2}) for (int stage = 0; stage <= 6; ++stage) {
        Fixture f; f.hdr = header(0, 6); auto& m = f.manager;
        void* input_owner = arena + 0x70000;
        if (stage < 6) m.BinTbl.NumDatTbl = stage;
        else m.EvdTbl.NumDatTbl = 0;
        const auto parents = f.parents; const auto bins = f.bins;
        f.observe(); assert(f.admit(flag, input_owner) == 0);
        assert(identical(f.parents, parents) && identical(f.bins, bins));
        assert(debug_frees.empty() && !transport_reads);
        m.BinTbl.NumDatTbl = 320; m.EvdTbl.NumDatTbl = 32;
        assert(f.admit(flag, input_owner) == 1); f.stop_observing(); f.complete();
        assert(f.parents[0].Dat == f.hdr && f.parents[0].dat2 == input_owner && f.parents[0].Count == 1);
        const auto committed_parents = f.parents; const auto committed_bins = f.bins;
        assert(f.admit(flag, arena + 0x71000) == 1);
        assert(identical(f.parents, committed_parents) && identical(f.bins, committed_bins));
        assert(debug_frees.empty());
    }
    for (int flag : {0, 2}) {
        Fixture f;
        // An invalid address reaches real SetBin's negative-address check.
        parts(f.hdr)[2].ofs = 0x80000000;
        const auto parents = f.parents; const auto bins = f.bins;
        assert(f.admit(flag, arena + 0x70000) == 0);
        assert(identical(f.parents, parents) && identical(f.bins, bins) && debug_frees.empty());
        parts(f.hdr)[2].ofs = 32768 + 2 * 32;
        assert(f.admit(flag) == 1); f.complete();
    }
    for (int stage = 0; stage < 4; ++stage) {
        Fixture f; auto* e = &parts(f.hdr)[stage];
        std::memset(e->name, 'x', sizeof(e->name)); // 48 chars, terminated in the offset's low byte.
        e->ofs = 0;
        const auto parents = f.parents; const auto bins = f.bins;
        assert(f.admit(2, arena + 0x70000) == 0);
        assert(identical(f.parents, parents) && identical(f.bins, bins) && debug_frees.empty());
        std::snprintf(e->name, sizeof(e->name), "part%03d.bin", stage); e->ofs = 32768 + stage * 32;
        assert(f.admit(2) == 1); f.complete();
    }
    {
        Fixture f; char too_long[49]; std::memset(too_long, 'x', 48); too_long[48] = 0;
        const auto parents = f.parents; const auto bins = f.bins;
        assert(f.manager.SetEvd(too_long, f.hdr, arena + 0x70000, 2) == 0);
        assert(identical(f.parents, parents) && identical(f.bins, bins) && debug_frees.empty());
        assert(f.admit(2) == 1);
    }
    std::cout << "every child/parent stage, malformed child/name, no publication/free, immediate retry and duplicate success PASS\n";
}

static void shared_owners() {
    for (int flag : {0, 2}) for (int old_flag : {0, 2}) for (unsigned old_count : {0U, 1U, 7U}) {
        Fixture f; auto& m = f.manager;
        assert(m.SetBin(parts(f.hdr)[0].name, arena + 0x100000, arena + 0x110000, old_flag) == 1);
        f.bins[0].Count = old_count;
        // Three references to one pre-existing bin must be rolled back exactly.
        std::strcpy(parts(f.hdr)[1].name, parts(f.hdr)[0].name);
        std::strcpy(parts(f.hdr)[2].name, parts(f.hdr)[0].name);
        m.BinTbl.NumDatTbl = 1;
        const auto parents = f.parents; const auto bins = f.bins;
        assert(f.admit(flag, arena + 0x70000) == 0);
        assert(identical(f.parents, parents) && identical(f.bins, bins) && debug_frees.empty());
        m.BinTbl.NumDatTbl = 320;
        assert(f.admit(flag) == 1 && f.bins[0].Count == old_count + 3);
        assert(f.bins[0].Dat == arena + 0x100000 && f.bins[0].dat2 == arena + 0x110000);
    }
    // Multi-reference newly created slots, including every new-slot mask edge.
    for (unsigned slot : {0U, 31U, 32U, 63U, 64U, 319U}) for (int flag : {0, 2}) {
        Fixture f; auto& m = f.manager;
        for (unsigned i = 0; i < slot; ++i) {
            char name[32]; std::snprintf(name, sizeof(name), "unrelated%03u.bin", i);
            assert(m.SetBin(name, arena + 0x100000 + i * 32, nullptr, 0) == 1);
        }
        std::strcpy(parts(f.hdr)[1].name, parts(f.hdr)[0].name);
        m.BinTbl.NumDatTbl = slot + 1;
        const auto parents = f.parents; const auto bins = f.bins;
        assert(f.admit(flag) == 0);
        assert(identical(f.parents, parents) && identical(f.bins, bins) && debug_frees.empty());
        m.BinTbl.NumDatTbl = 320;
        // At slot319 only one distinct bin can fit: reduce the header for retry.
        f.hdr->nBin = slot == 319 ? 2 : 4;
        assert(f.admit(flag) == 1 && f.bins[slot].Count == 2); f.complete();
    }
    for (unsigned old_count : {32766U, 32767U, 65535U}) {
        Fixture f; auto& m = f.manager;
        assert(m.SetBin(parts(f.hdr)[0].name, arena + 0x100000, nullptr, 0) == 1);
        f.bins[0].Count = old_count;
        std::strcpy(parts(f.hdr)[1].name, parts(f.hdr)[0].name);
        const auto parents = f.parents; const auto bins = f.bins;
        assert(f.admit() == 0);
        assert(identical(f.parents, parents) && identical(f.bins, bins));
        f.bins[0].Count = 1;
        assert(f.admit() == 1 && f.bins[0].Count == 3);
    }
    for (int flag : {0, 2}) {
        Fixture f; f.hdr = header(0, 321);
        const auto parents = f.parents; const auto bins = f.bins;
        assert(f.admit(flag, arena + 0x70000) == 0);
        assert(identical(f.parents, parents) && identical(f.bins, bins) && debug_frees.empty());
        f.hdr->nBin = 320;
        assert(f.admit(flag) == 1); f.complete();
        for (const auto& bin : f.bins) assert(bin.Count == 1);
        const auto committed = f.bins;
        assert(f.admit(flag) == 1 && identical(f.bins, committed));
    }
    std::cout << "shared/permanent/debug owners, zero/high counts, repeated names and all journal mask boundaries PASS\n";
}

static void existing_parent_controls() {
    for (int flag : {0, 2}) {
        Fixture f; auto& m = f.manager;
        assert(m.EvdTbl.SetDat(parent_name, f.hdr, 8, arena + 0x70000, flag, nullptr) == 1);
        assert(m.SetBin(parts(f.hdr)[0].name, arena + 0x100000, arena + 0x110000, 2) == 1);
        const auto parents = f.parents; const auto bins = f.bins;
        assert(f.admit(flag) == 0); // Old partial state is never called complete.
        assert(identical(f.parents, parents) && identical(f.bins, bins) && debug_frees.empty());
        auto* other = header(0x10000, 0);
        assert(m.SetEvd(parent_name, other, arena + 0x72000, flag) == 0);
        assert(identical(f.parents, parents) && identical(f.bins, bins));
        for (int i = 1; i < f.hdr->nBin; ++i)
            assert(m.SetBin(parts(f.hdr)[i].name, reinterpret_cast<u8*>(f.hdr) + parts(f.hdr)[i].ofs, nullptr, flag) == 1);
        const auto complete_parents = f.parents; const auto complete_bins = f.bins;
        assert(f.admit(flag) == 1);
        assert(identical(f.parents, complete_parents) && identical(f.bins, complete_bins));
        // Different incoming bytes cannot change the registered header/bins.
        assert(m.SetEvd(parent_name, other, arena + 0x72000, flag) == 1);
        assert(identical(f.parents, complete_parents) && identical(f.bins, complete_bins) && debug_frees.empty());
    }
    for (int invalid : {0, 1, 2, 3, 4}) {
        Fixture f; assert(f.admit() == 1);
        if (invalid == 0) f.parents[0].Etc = 7;
        if (invalid == 1) f.parents[0].Dat = reinterpret_cast<void*>(0x1000);
        if (invalid == 2) f.bins[2].Etc = 8;
        if (invalid == 3) f.bins[2].Dat = nullptr;
        if (invalid == 4) f.bins[2].Dat = reinterpret_cast<void*>(0x1000);
        const auto parents = f.parents; const auto bins = f.bins;
        assert(f.admit() == 0);
        assert(identical(f.parents, parents) && identical(f.bins, bins) && debug_frees.empty());
    }
    for (int flag : {0, 2}) {
        Fixture f; auto& m = f.manager;
        auto* prior = header(0x10000, 2); char prior_name[] = "prior.evd";
        assert(m.SetEvd(prior_name, prior, arena + 0x72000, 2) == 1);
        m.BinTbl.NumDatTbl = 3;
        const auto parents = f.parents; const auto bins = f.bins;
        assert(f.admit(flag, arena + 0x70000) == 0);
        assert(identical(f.parents, parents) && identical(f.bins, bins) && debug_frees.empty());
        void* owner = nullptr;
        assert(m.GetEvd(&owner, prior_name, 1) == 1 && owner == prior);
        m.BinTbl.NumDatTbl = 320;
        assert(f.admit(flag, arena + 0x70000) == 1);
        assert(f.bins[0].Count == 2 && f.bins[0].Dat == reinterpret_cast<u8*>(prior) + parts(prior)[0].ofs);
        assert(m.GetEvd(&owner, parent_name, 1) == 1 && owner == f.hdr);
        assert(m.DelEvd(parent_name) == 1 && f.bins[0].Count == 1);
        assert(m.GetEvd(&owner, prior_name, 1) == 1 && owner == prior);
        assert(m.DelEvd(prior_name) == 1 && !m.BinTbl.ChkDat(parts(prior)[0].name));
    }
    std::cout << "legacy partial-owner refusal, unchanged duplicate ownership and invalid registration controls PASS\n";
}

static void retirement_controls() {
    for (int flag : {0, 2}) {
        Fixture f; auto& m = f.manager;
        assert(m.SetBin(parts(f.hdr)[0].name, arena + 0x100000, arena + 0x110000, 2) == 1);
        assert(f.admit(flag, arena + 0x70000) == 1);
        assert(m.DelEvd(parent_name) == 1);
        assert(f.bins[0].Count == 1 && f.bins[0].Dat == arena + 0x100000);
        assert(f.bins[0].dat2 == arena + 0x110000);
        if (flag == 2) {
            assert(!m.EvdTbl.ChkDat(parent_name) && !m.BinTbl.ChkDat(parts(f.hdr)[1].name));
            assert(debug_frees.size() == 1 && debug_frees[0] == arena + 0x70000);
            assert(f.admit(flag, arena + 0x70000) == 1);
        } else {
            // Existing permanent-table contract: entries remain with zero refs.
            assert(m.EvdTbl.ChkDat(parent_name) && f.parents[0].Count == 0);
            assert(m.BinTbl.ChkDat(parts(f.hdr)[1].name) && f.bins[1].Count == 0);
            assert(debug_frees.empty());
            const auto parents = f.parents; const auto bins = f.bins;
            assert(f.admit(flag) == 1);
            assert(identical(f.parents, parents) && identical(f.bins, bins));
        }
        m.ToolCoreEvdDel();
        assert(!m.EvdTbl.ChkDat(parent_name) && !m.BinTbl.ChkDat(parts(f.hdr)[0].name));
        assert(f.admit(flag) == 1); f.complete();
    }
    {
        Fixture f; EventMgr m{};
        // Real myRoomInit/init/end, with the source heap at the host boundary.
        assert(m.myRoomInit() == 1);
        assert(m.EvdTbl.NumDatTbl == 32 && m.BinTbl.NumDatTbl == 320);
        assert(m.SetEvd(parent_name, f.hdr, arena + 0x70000, 2) == 1);
        assert(m.EvdTbl.end() && m.BinTbl.end() && m.FuncTbl.end() && m.ReadTbl.end());
        assert(debug_frees.size() == 1 && !m.EvdTbl.pWork && !m.BinTbl.pWork);
        assert(m.myRoomInit() == 1 && !m.EvdTbl.ChkDat(parent_name));
        auto* next_generation = header(0x10000, 2);
        assert(m.SetEvd(parent_name, next_generation, arena + 0x72000, 2) == 1);
        assert(m.EvdTbl.pWork[0].Dat == next_generation);
        assert(m.EvdTbl.end() && m.BinTbl.end() && m.FuncTbl.end() && m.ReadTbl.end());
        assert(debug_frees.size() == 2 && debug_frees[1] == arena + 0x72000);
    }
    std::cout << "actual DelEvd/shared-bin retirement, permanent rows, tool clear and table end/room reinit PASS\n";
}

static void invalid_inputs() {
    for (int fault = 0; fault < 7; ++fault) {
        Fixture f; auto& m = f.manager;
        const auto parents = f.parents; const auto bins = f.bins;
        if (fault == 0) f.hdr->tag[0] = 'X';
        if (fault == 1) f.hdr = nullptr;
        if (fault == 2) f.hdr->nBin = -1;
        if (fault == 3) m.EvdTbl.pWork = nullptr;
        if (fault == 4) m.BinTbl.pWork = nullptr;
        if (fault == 5) m.BinTbl.NumDatTbl = -1;
        if (fault == 6) m.BinTbl.NumDatTbl = 321;
        assert(f.admit(2, arena + 0x70000) == 0);
        assert(identical(f.parents, parents) && identical(f.bins, bins) && debug_frees.empty());
    }
    { Fixture f; f.hdr->nBin = 0; assert(f.admit() == 1); f.complete(); }
    std::cout << "invalid input/table guards and zero-bin positive control PASS\n";
}

int main() {
    arena = static_cast<unsigned char*>(mmap(reinterpret_cast<void*>(0x90000000), 0x200000,
        PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANONYMOUS | MAP_FIXED_NOREPLACE, -1, 0));
    assert(arena == reinterpret_cast<void*>(0x90000000));
    failures_and_retry(); shared_owners(); existing_parent_controls(); retirement_controls(); invalid_inputs();
    for (auto p : table_allocations) assert(p == nullptr);
    assert(!transport_reads && publication_observations > 0);
    std::cout << "EVENT_TXN_CASES=" << cases << " publication_observations=" << publication_observations << " PASS\n";
    munmap(arena, 0x200000);
}
