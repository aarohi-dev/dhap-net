"""
Step 2 – Fetch flows.txt slice and dns.txt.gz.

Budget plan (from pilot):
  - flows.txt @ 111 MB/day  →  days 0-14 (t=0..1,296,000 s) = ~1.67 GB
  - dns.txt.gz (full)                                         =  0.185 GB
  - TOTAL                                                     ~ 1.86 GB < 2 GB budget

Covers 663/749 red-team events (88.5%). Days 15-29 sacrificed to stay in budget.

Uses HfFileSystem.open() which supports seek() for large files.

Run: python data/03_fetch_slice.py
"""

import sys, json, csv, time, io
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from configs.config import (
    HF_REPO, HF_PREFIX, DATA_DIR, REPORTS_DIR, DOWNLOAD_LEDGER,
    DOWNLOAD_BUDGET_GB
)

from huggingface_hub import HfFileSystem
import requests

FLOWS_REL   = f"{HF_PREFIX}/flows.txt"
DNS_REL     = f"{HF_PREFIX}/dns.txt.gz"
CHUNK_SIZE  = 8 * 1024 * 1024     # 8 MB per read

# t_end override: trim to day 15 to fit in budget
T_END_TRIM  = 15 * 86400          # 1,296,000 s

# ── ledger helpers ─────────────────────────────────────────────────────────────
def get_cumulative_bytes():
    if not DOWNLOAD_LEDGER.exists():
        return 0
    with open(DOWNLOAD_LEDGER) as f:
        rows = list(csv.DictReader(f))
    return int(rows[-1]["cumulative_bytes"]) if rows else 0

def ledger_append(filename, bytes_fetched, cumulative):
    write_header = not DOWNLOAD_LEDGER.exists()
    with open(DOWNLOAD_LEDGER, "a", newline="") as f:
        w = csv.writer(f)
        if write_header:
            w.writerow(["timestamp","file","bytes_fetched","cumulative_bytes"])
        w.writerow([time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime()),
                    filename, bytes_fetched, cumulative])

# ── binary search via HfFileSystem ────────────────────────────────────────────
def binary_search_offset(fs: HfFileSystem, hf_path: str,
                         file_size: int, target_time: int,
                         block: int = 131072) -> int:
    """Return byte offset where time >= target_time (approximate)."""
    if target_time <= 0:
        return 0
    lo, hi = 0, file_size
    while hi - lo > block:
        mid = (lo + hi) // 2
        with fs.open(hf_path, "rb") as f:
            f.seek(mid)
            chunk = f.read(block)
        text  = chunk.decode("utf-8", errors="replace")
        lines = text.split("\n")
        t = None
        for ln in lines[1:]:
            parts = ln.strip().split(",")
            if len(parts) >= 1:
                try:
                    t = int(parts[0])
                    break
                except ValueError:
                    continue
        if t is None or t < target_time:
            lo = mid
        else:
            hi = mid
    return lo

# ── stream and save flows slice ────────────────────────────────────────────────
def fetch_flows_slice(t_start: int, t_end: int,
                      budget_remaining: float) -> int:
    fs      = HfFileSystem()
    hf_path = f"datasets/{HF_REPO}/{FLOWS_REL}"

    # File size from pilot
    file_size = 5_237_189_507

    # Find start offset
    if t_start > 0:
        print(f"\n[Fetch] Binary-searching start offset for t_start={t_start:,} ...")
        start_off = binary_search_offset(fs, hf_path, file_size, t_start)
        print(f"  Start byte offset: {start_off:,}")
    else:
        start_off = 0
        print(f"\n[Fetch] t_start=0, starting from beginning of file")

    out_path = DATA_DIR / "flows_slice.txt"
    total_bytes   = 0
    lines_written = 0
    t_seen_max    = 0
    past_end      = False

    t0 = time.time()
    print(f"[Fetch] Streaming flows.txt from offset {start_off:,} until t={t_end:,} ...")
    print(f"  Budget for flows: {budget_remaining/1e9:.3f} GB")

    leftover = b""  # incomplete line buffer

    with fs.open(hf_path, "rb") as f_in, open(out_path, "wb") as f_out:
        f_in.seek(start_off)

        while True:
            if total_bytes >= budget_remaining:
                print(f"\n[BUDGET] Flows budget exhausted at {total_bytes/1e9:.3f} GB.")
                break

            to_read = min(CHUNK_SIZE, int(budget_remaining - total_bytes))
            chunk   = f_in.read(to_read)
            if not chunk:
                break

            total_bytes += len(chunk)

            # Process lines
            data  = leftover + chunk
            parts_raw = data.split(b"\n")
            leftover  = parts_raw[-1]  # may be incomplete

            for line_b in parts_raw[:-1]:
                ln = line_b.decode("utf-8", errors="replace").strip()
                fields = ln.split(",")
                if len(fields) < 9:
                    continue
                try:
                    t = int(fields[0])
                except ValueError:
                    continue
                if t < t_start:
                    continue
                if t > t_end:
                    past_end = True
                    break
                f_out.write(line_b + b"\n")
                lines_written += 1
                t_seen_max = max(t_seen_max, t)

            if past_end:
                print(f"\n[Fetch] Reached t_end={t_end:,} s at {total_bytes/1e9:.3f} GB")
                break

            elapsed = time.time() - t0
            speed   = total_bytes / elapsed / 1e6
            print(f"\r  {total_bytes/1e9:.3f} GB  {lines_written:,} lines  "
                  f"{speed:.1f} MB/s  {elapsed:.0f}s elapsed ...", end="", flush=True)

    elapsed = time.time() - t0
    print(f"\n[Fetch] Done. {total_bytes/1e6:.1f} MB fetched in {elapsed:.0f}s, "
          f"{lines_written:,} lines, max_t={t_seen_max:,} s")

    return total_bytes

# ── download dns.txt.gz ───────────────────────────────────────────────────────
def fetch_dns(budget_remaining: float) -> int:
    dns_size = 185_104_940
    if dns_size > budget_remaining:
        print(f"\n[DNS] dns.txt.gz ({dns_size/1e6:.0f} MB) > remaining budget; skipping.")
        return 0

    print(f"\n[Fetch] Downloading dns.txt.gz ({dns_size/1e6:.0f} MB) ...")
    fs      = HfFileSystem()
    hf_path = f"datasets/{HF_REPO}/{DNS_REL}"
    out     = DATA_DIR / "dns.txt.gz"

    total = 0
    t0    = time.time()
    with fs.open(hf_path, "rb") as f_in, open(out, "wb") as f_out:
        while True:
            chunk = f_in.read(CHUNK_SIZE)
            if not chunk:
                break
            f_out.write(chunk)
            total += len(chunk)
            print(f"\r  {total/1e6:.0f} / {dns_size/1e6:.0f} MB ...", end="", flush=True)

    elapsed = time.time() - t0
    print(f"\n  dns.txt.gz: {total/1e6:.1f} MB in {elapsed:.0f}s -> {out}")
    return total

# ── main ──────────────────────────────────────────────────────────────────────
def main():
    with open(REPORTS_DIR / "slice_window.json") as f:
        sw = json.load(f)

    t_start = int(sw["t_start"])
    t_end   = min(int(sw["t_end"]), T_END_TRIM)   # trim to fit budget

    print(f"\n[Fetch] Budget-trimmed slice: t_start={t_start:,} s  t_end={t_end:,} s "
          f"({t_end/86400:.1f} days)")
    print(f"  Red-team events in this window: days 1-14 = 663/749 (88.5%)")

    cum_before     = get_cumulative_bytes()
    budget_bytes   = DOWNLOAD_BUDGET_GB * 1e9
    budget_rem     = budget_bytes - cum_before
    dns_reserve    = 185_104_940 + 50_000_000   # DNS + 50 MB safety margin
    flows_budget   = budget_rem - dns_reserve

    print(f"\n[Fetch] Budget remaining: {budget_rem/1e9:.3f} GB")
    print(f"  Flows budget:  {flows_budget/1e9:.3f} GB")
    print(f"  DNS reserve:   {dns_reserve/1e6:.0f} MB")

    # Fetch flows
    flows_bytes = fetch_flows_slice(t_start, t_end, flows_budget)
    cum_after   = cum_before + flows_bytes
    ledger_append(FLOWS_REL + " [slice]", flows_bytes, cum_after)
    print(f"[Ledger] flows slice: {flows_bytes/1e6:.1f} MB  cumulative: {cum_after/1e6:.1f} MB")

    # Fetch DNS
    budget_for_dns = budget_bytes - cum_after
    dns_bytes = fetch_dns(budget_for_dns)
    if dns_bytes > 0:
        cum_after += dns_bytes
        ledger_append(DNS_REL, dns_bytes, cum_after)

    print(f"\n--- Download ledger summary ---")
    print(f"  flows slice : {flows_bytes/1e6:.1f} MB")
    print(f"  dns.txt.gz  : {dns_bytes/1e6:.1f} MB")
    print(f"  Cumulative  : {cum_after/1e6:.1f} MB  ({cum_after/1e9:.3f} / {DOWNLOAD_BUDGET_GB} GB)")

    # Update slice_window with trimmed t_end
    sw["t_end"]        = t_end
    sw["t_end_trimmed"]= True
    sw["slice_days"]   = (t_end - t_start) / 86400
    sw["rt_events_covered"] = 663
    sw["rt_events_total"]   = 749
    with open(REPORTS_DIR / "slice_window.json", "w") as f:
        json.dump(sw, f, indent=2)

    meta = {
        "t_start": t_start, "t_end": t_end,
        "flows_bytes": flows_bytes, "dns_bytes": dns_bytes,
        "cumulative_bytes": cum_after,
        "flows_out": str(DATA_DIR / "flows_slice.txt"),
        "dns_out":   str(DATA_DIR / "dns.txt.gz"),
    }
    with open(REPORTS_DIR / "fetch_meta.json", "w") as f:
        json.dump(meta, f, indent=2)

    print(f"\n[Fetch] Done. Proceed to 04_spark_etl.py")

if __name__ == "__main__":
    main()
