// Included inside v2 only for DISC_PIO_FALLBACK=1. The controller is shared
// with the fake-driver gate; this adapter supplies the actual KOS/BIOS calls.
using re4dc::disc_pio::Command;
using re4dc::disc_pio::Request;
using re4dc::disc_pio::Result;
static re4dc::disc_pio::State pio_state;

struct PioDriver {
    cd_read_params_t params = {};
    uint64_t now() const { return timer_ms_gettime64(); }
    bool acquire() const { return sem_wait_timed(&_g1_ata_sem, 30000) == 0; }
    void release() const { sem_signal(&_g1_ata_sem); }
    void pause(uint64_t start, unsigned spins, bool landing) const {
        const unsigned spin_ms = landing ? RE4DC_DISC_LAND_SPIN_MS : RE4DC_DISC_POLL_SPIN_MS;
        if (spins < 64 || now() - start < spin_ms) thd_pass();
        else thd_sleep(1);
    }
    void prepare(const Request& r, bool dma) const {
        const size_t bytes = r.count * 2048;
        if (aligned32(r.buffer, bytes)) mark(r.buffer, bytes);
        if (dma && cached(r.buffer)) dcache_inval_range((uintptr_t) r.buffer, bytes);
    }
    int submit(const Request& r, bool dma) {
#if defined(RE4DC_FALLBACK_AUDIT29) && RE4DC_FALLBACK_AUDIT29
        if(!dma)re4dc::fa29::hit(re4dc::fa29::DiscPioRetry,unsigned(r.count)*2048U);
#endif
#line 24
        params.start_sec = r.sector;
        params.num_sec = r.count;
        params.buffer = dma ? (void*) ((uintptr_t) r.buffer & 0x1fffffffu) : r.buffer;
        params.is_test = 0;
        const int handle = syscall_gdrom_send_command(dma ? CD_CMD_DMAREAD : CD_CMD_PIOREAD, &params);
        syscall_gdrom_exec_server();
        return handle;
    }
    int submit_init() const {
        const int handle = syscall_gdrom_send_command(CD_CMD_INIT, nullptr);
        syscall_gdrom_exec_server();
        return handle;
    }
    Command check(int handle) const {
        syscall_gdrom_exec_server();
        cd_cmd_chk_status_t st = {};
        const int result = syscall_gdrom_check_command(handle, &st);
        if (result <= CD_CMD_FAILED)
            return st.err1 == 2 ? Command::no_disc : st.err1 == 6 ? Command::disc_changed : Command::failed;
        if (result == CD_CMD_COMPLETED || result == CD_CMD_NOT_FOUND) return Command::done;
        // STREAMING is not completion of this sector command.
        return Command::pending;
    }
    bool engine_busy() const { return (*(volatile uint32_t*) 0xa05f7418u & 1u) != 0; }
    bool landed(const Request& r) const {
        return !aligned32(r.buffer, r.count * 2048) || marker_gone(r.buffer, r.count * 2048);
    }
    void disable_dma() const {
        const int old = irq_disable();
        *(volatile uint32_t*) 0xa05f7414u = 0;
        irq_restore(old);
    }
    void enable_dma() const {
        const int old = irq_disable();
        *(volatile uint32_t*) 0xa05f7414u = 1;
        irq_restore(old);
    }
    void clear_events() const {
        const int old = irq_disable();
        *(volatile uint32_t*) ASIC_ACK_A = 1u << (ASIC_EVT_GD_DMA & 31u);
        *(volatile uint32_t*) ASIC_ACK_C = (1u << (ASIC_EVT_GD_DMA_OVERRUN & 31u)) |
                                          (1u << (ASIC_EVT_GD_DMA_ILLADDR & 31u));
        irq_restore(old);
    }
    void abort(int handle) const { syscall_gdrom_abort_command(handle); }
    void reset() const { syscall_gdrom_reset(); syscall_gdrom_init(); }
    bool sector_mode_2048() const {
        cd_check_drive_status_t ds = {};
        syscall_gdrom_check_drive(&ds);
        cd_sec_mode_params_t p = {};
        p.rw = 0;
        p.sector_part = CDROM_READ_DATA_AREA;
        p.track_type = ds.disc_type == CD_CDROM_XA ? 2048 : 1024;
        p.sector_size = 2048;
        return syscall_gdrom_sector_mode(&p) >= 0;
    }
    void switched(Result result, bool session, unsigned failures) const {
        const char* reason = result == Result::timeout ? "DMA timeout" :
                             result == Result::missing ? "DMA data check" : "DMA error";
        re4dc_log("DISC: DMA->PIO after %s (%s, consecutive=%u)\n", reason,
                  session ? "session" : "same sectors", failures);
    }
};

int pio_read(void* buffer, uint32_t sector, size_t count, bool dma) {
    PioDriver driver;
    const Result result = re4dc::disc_pio::read(driver, pio_state, {buffer, sector, count}, dma);
    if (result == Result::unsafe)
        fatal("disc: DMA would not retire; buffer held");
    if (result == Result::lock_timeout)
        fatal("disc: drive ownership timed out; no retry");
    if (result == Result::ok) return ERR_OK;
    if (result == Result::no_disc) return ERR_NO_DISC;
    if (result == Result::disc_changed) return ERR_DISC_CHG;
    return result == Result::timeout ? ERR_TIMEOUT : ERR_SYS;
}

void pio_validation_begin() {
    PioDriver driver;
    if (!driver.acquire()) fatal("disc: validation ownership timed out");
    pio_state.validation_begin();
    driver.release();
}
void pio_validation_reject() {
    PioDriver driver;
    if (!driver.acquire()) fatal("disc: retry ownership timed out");
    if (pio_state.validation_reject())
        re4dc_log("DISC: DMA->PIO after first-read check (%s, consecutive=%u)\n",
                  pio_state.session_pio ? "session" : "whole-file retry", pio_state.failures);
    driver.release();
}
void pio_validation_end() {
    PioDriver driver;
    if (!driver.acquire()) fatal("disc: validation end ownership timed out");
    pio_state.validation_end();
    driver.release();
}
