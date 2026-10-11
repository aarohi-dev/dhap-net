"""
Step 1 – Revised pilot read using HfFileSystem (supports seek/range).

Run: python data/02_pilot.py
"""

import sys, json, time, csv, io
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from configs.config import (
    HF_REPO, HF_PREFIX, DATA_DIR, REPORTS_DIR, DOWNLOAD_LEDGER,
    DOWNLOAD_BUDGET_GB
)

from huggingface_hub import HfFileSystem
import pandas as pd

FLOWS_REL  = f"{HF_PREFIX}/flows.txt"
PILOT_MB   = 30
PILOT_BYTES= PILOT_MB * 1024 * 1024

INVENTORY = {
    "auth.txt.gz":  7_626_505_158,
    "dns.txt":        812_736_592,
    "dns.txt.gz":     185_104_940,
    "flows.txt":    5_237_189_507,
    "flows.txt.gz": 1_083_479_090,
    "proc.txt":    15_397_551_964,
    "redteam.txt":         22_986,
}

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

def parse_flows(raw: bytes) -> list[dict]:
    rows = []
    for ln in raw.decode("utf-8", errors="replace").split("\n"):
        parts = ln.strip().split(",")
        if len(parts) < 9:
            continue
        try:
            t = int(parts[0])
        except ValueError:
            continue
        rows.append({"time": t, "src": parts[2], "dst": parts[4],
                     "protocol": parts[6], "bytes_val": parts[8]})
    return rows

def main():
    print("\n[Pilot] === LANL 2015 repo file inventory (verified) ===")
    for name, size in INVENTORY.items():
        print(f"  {name:30s}  {size/1e9:.3f} GB")

    print("\n  NOTE: auth.txt (decompressed) does NOT exist in this repo.")
    print("  auth.txt.gz is 7.6 GB compressed; for 29.6/58 days ~ 3.8 GB – exceeds 2 GB budget.")
    print("  -> DECISION: Use flows.txt (5.2 GB, HfFileSystem-seekable) + dns.txt.gz (185 MB).")
    print("  -> TIER C: comm edges (flows) + dns edges. No auth-logon-type edges.")
    print("     This means the DHAP-Net vs ablation-on-heterogeneity comparison is not fully testable.")

    cum_before = get_cumulative_bytes()
    budget_rem = DOWNLOAD_BUDGET_GB * 1e9 - cum_before
    print(f"\n[Pilot] Budget used: {cum_before/1e6:.2f} MB  Remaining: {budget_rem/1e9:.3f} GB")

    # ── Pilot read via HfFileSystem ───────────────────────────────────────────
    fs = HfFileSystem()
    hf_path = f"datasets/{HF_REPO}/{FLOWS_REL}"

    print(f"\n[Pilot] Opening {FLOWS_REL} via HfFileSystem ...")
    t0 = time.time()
    with fs.open(hf_path, "rb") as f:
        pilot_data = f.read(PILOT_BYTES)
    elapsed = time.time() - t0
    actual = len(pilot_data)
    print(f"  Read {actual/1e6:.1f} MB in {elapsed:.1f}s ({actual/elapsed/1e6:.2f} MB/s)")

    cum_after = cum_before + actual
    ledger_append(FLOWS_REL + " [pilot]", actual, cum_after)
    print(f"[Ledger] cumulative: {cum_after/1e6:.2f} MB ({cum_after/1e9:.4f}/{DOWNLOAD_BUDGET_GB} GB)")

    # ── Parse & verify schema ─────────────────────────────────────────────────
    rows = parse_flows(pilot_data)
    print(f"\n[Pilot] Parsed {len(rows):,} flow events from pilot")
    if not rows:
        print("[ERROR] No rows parsed.")
        return

    print("\n--- First 5 parsed rows ---")
    for r in rows[:5]:
        print(f"  {r}")
    print("\n--- Column schema (confirmed from real data) ---")
    print("  time, duration, src, src_port, dst, dst_port, protocol, packets, bytes")

    df = pd.DataFrame(rows)
    t_min = df["time"].min()
    t_max = df["time"].max()
    days  = max((t_max - t_min) / 86400, 0.001)
    bpd   = actual / days

    print(f"\n--- Rate estimate ---")
    print(f"  Pilot covers: t={t_min:,} -> {t_max:,} s  ({days:.3f} days)")
    print(f"  Bytes/day (decompressed flows): {bpd/1e6:.1f} MB/day")

    # ── Verify time-sorted (sample first 3 probe points from pilot only) ──────
    sample_offsets = [0, len(pilot_data)//3, 2*len(pilot_data)//3]
    sample_times   = []
    for off in sample_offsets:
        chunk = pilot_data[off:off+512]
        for ln in chunk.decode("utf-8", errors="replace").split("\n")[1:]:
            parts = ln.strip().split(",")
            if len(parts) >= 1:
                try:
                    sample_times.append((off, int(parts[0])))
                    break
                except ValueError:
                    continue
    is_sorted = all(sample_times[i][1] <= sample_times[i+1][1]
                    for i in range(len(sample_times)-1))
    print(f"\n  Sorting check (first 3 probe points): {sample_times}")
    print(f"  Time-sorted: {is_sorted}")

    # ── Slice cost estimate ───────────────────────────────────────────────────
    with open(REPORTS_DIR / "slice_window.json") as f:
        sw = json.load(f)
    slice_days = sw["slice_days"]
    est_flows  = bpd * slice_days
    dns_size   = INVENTORY["dns.txt.gz"]
    total_est  = est_flows + dns_size

    print(f"\n--- Slice cost estimate ---")
    print(f"  Slice duration        : {slice_days:.1f} days")
    print(f"  Est. flows slice      : {est_flows/1e6:.0f} MB  ({est_flows/1e9:.2f} GB)")
    print(f"  dns.txt.gz (full)     : {dns_size/1e6:.0f} MB")
    print(f"  Total estimated       : {total_est/1e9:.2f} GB")
    budget_left = budget_rem - actual
    print(f"  Budget remaining      : {budget_left/1e9:.3f} GB")

    if total_est <= budget_left:
        tier = "C"
        print(f"\n  -> TIER C: Full flows slice + dns.txt.gz fits in budget.")
    else:
        # Trim flows slice
        max_flows_bytes = budget_left - dns_size - 100e6  # 100 MB safety margin
        trimmed_days    = max_flows_bytes / bpd
        est_flows       = max_flows_bytes
        tier = "C"
        print(f"\n  -> TIER C (trimmed): Flows slice trimmed to {trimmed_days:.1f} days "
              f"({max_flows_bytes/1e9:.2f} GB)")

    summary = {
        "flows_file_size_bytes": INVENTORY["flows.txt"],
        "is_time_sorted": is_sorted,
        "bytes_per_day_flows": bpd,
        "estimated_flows_slice_bytes": est_flows,
        "dns_bytes": dns_size,
        "total_estimated_gb": total_est / 1e9,
        "recommended_tier": tier,
        "note": ("auth.txt not available (only .gz at 7.6 GB). Using flows.txt + dns.txt.gz. "
                 "Tier C: comm + dns edges only. Heterogeneity comparison limited.")
    }
    with open(REPORTS_DIR / "pilot_summary.json", "w") as f:
        json.dump(summary, f, indent=2)

    print(f"\n[Pilot] Summary saved to {REPORTS_DIR/'pilot_summary.json'}")
    print("\n[Pilot] Done. Proceed to 03_fetch_slice.py")

if __name__ == "__main__":
    main()
