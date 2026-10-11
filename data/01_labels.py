"""
Step 0 - Download the red-team label file and print statistics.
Tracks the download ledger and determines the red-team window.

Run: python data/01_labels.py
"""

import sys, os, csv, io, time
import io as _io
from pathlib import Path
# Force UTF-8 output on Windows
if sys.stdout.encoding != 'utf-8':
    sys.stdout = _io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# ── path setup ────────────────────────────────────────────────────────────────
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from configs.config import (
    HF_REPO, HF_PREFIX, DATA_DIR, REPORTS_DIR, DOWNLOAD_LEDGER, LEADN_DAYS,
    DOWNLOAD_BUDGET_GB
)

import requests
import pandas as pd

# ── ledger helper ─────────────────────────────────────────────────────────────
def ledger_append(filename: str, bytes_fetched: int, cumulative: int):
    write_header = not DOWNLOAD_LEDGER.exists()
    with open(DOWNLOAD_LEDGER, "a", newline="") as f:
        w = csv.writer(f)
        if write_header:
            w.writerow(["timestamp", "file", "bytes_fetched", "cumulative_bytes"])
        w.writerow([
            time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            filename, bytes_fetched, cumulative
        ])

def get_cumulative_bytes() -> int:
    if not DOWNLOAD_LEDGER.exists():
        return 0
    with open(DOWNLOAD_LEDGER) as f:
        rows = list(csv.DictReader(f))
    return int(rows[-1]["cumulative_bytes"]) if rows else 0

# ── resolve HuggingFace direct URL ────────────────────────────────────────────
def hf_url(filename: str) -> str:
    """Return the raw download URL for a file in the HF dataset repo."""
    return f"https://huggingface.co/datasets/{HF_REPO}/resolve/main/{filename}"

# ── download redteam.txt ──────────────────────────────────────────────────────
def download_redteam() -> bytes:
    rel_path = f"{HF_PREFIX}/redteam.txt"
    url = hf_url(rel_path)
    print(f"[Step 0] Fetching: {url}")

    cum_before = get_cumulative_bytes()
    r = requests.get(url, timeout=60)
    r.raise_for_status()
    content = r.content
    n_bytes = len(content)

    cum_after = cum_before + n_bytes
    ledger_append(rel_path, n_bytes, cum_after)

    budget_used_gb = cum_after / 1e9
    print(f"[Ledger] {rel_path}: {n_bytes:,} bytes   cumulative: {cum_after:,} B  "
          f"({budget_used_gb:.4f} / {DOWNLOAD_BUDGET_GB} GB)")

    # Save locally
    out = DATA_DIR / "redteam.txt"
    out.write_bytes(content)
    print(f"[Step 0] Saved to {out}")
    return content

# ── parse and print statistics ────────────────────────────────────────────────
def analyse_redteam(content: bytes) -> pd.DataFrame:
    lines = content.decode("utf-8").strip().split("\n")
    print(f"\n[Step 0] Total lines (events): {len(lines):,}")

    records = []
    for line in lines:
        parts = line.strip().split(",")
        if len(parts) < 4:
            continue
        t, user, src, dst = int(parts[0]), parts[1], parts[2], parts[3]
        records.append({"time": t, "user": user, "src": src, "dst": dst})

    df = pd.DataFrame(records)
    df["day"] = df["time"] // 86400
    df["hour"] = df["time"] // 3600

    print(f"\n--- Red-team statistics ---")
    print(f"  Events total       : {len(df):,}")
    print(f"  Distinct users     : {df['user'].nunique():,}")
    print(f"  Distinct src hosts : {df['src'].nunique():,}")
    print(f"  Distinct dst hosts : {df['dst'].nunique():,}")
    print(f"  Min time (s)       : {df['time'].min():,}   (day {df['time'].min()//86400})")
    print(f"  Max time (s)       : {df['time'].max():,}   (day {df['time'].max()//86400})")

    print(f"\n--- Events per day ---")
    per_day = df.groupby("day").size().reset_index(name="n_events")
    for _, row in per_day.iterrows():
        print(f"  Day {int(row.day):3d}: {int(row.n_events):4d} events")

    # Foothold vs spread
    src_only = set(df["src"].unique()) - set(df["dst"].unique())
    dst_any  = set(df["dst"].unique())
    print(f"\n--- Compromise types ---")
    print(f"  Initial footholds (src only, never a dst): {len(src_only):,}")
    print(f"  Hosts reached as dst (compromised via auth): {len(dst_any):,}")

    return df

# ── compute and save the slice window ────────────────────────────────────────
def compute_slice(df: pd.DataFrame) -> dict:
    t_first = int(df["time"].min())
    t_last  = int(df["time"].max())
    t_start = t_first - LEADN_DAYS * 86400   # lead-in
    t_start = max(t_start, 0)                # never negative
    t_end   = t_last + 3600                  # 1-hour buffer after last event

    info = {
        "t_first_redteam": t_first,
        "t_last_redteam":  t_last,
        "t_start":         t_start,
        "t_end":           t_end,
        "lead_in_days":    LEADN_DAYS,
        "slice_days":      (t_end - t_start) / 86400,
    }

    print(f"\n--- Slice window ---")
    print(f"  First red-team event : {t_first:,} s  (day {t_first//86400})")
    print(f"  Last  red-team event : {t_last:,} s  (day {t_last//86400})")
    print(f"  Lead-in days         : {LEADN_DAYS}")
    print(f"  t_start              : {t_start:,} s  (day {t_start//86400})")
    print(f"  t_end                : {t_end:,} s  (day {t_end//86400})")
    print(f"  Slice duration       : {info['slice_days']:.1f} days")

    # Write slice info for downstream scripts
    import json
    slice_file = REPORTS_DIR / "slice_window.json"
    with open(slice_file, "w") as f:
        json.dump(info, f, indent=2)
    print(f"\n[Step 0] Slice info saved to {slice_file}")

    return info

# ── main ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    content = download_redteam()
    df      = analyse_redteam(content)
    info    = compute_slice(df)

    # Save the label dataframe
    out_csv = DATA_DIR / "redteam_labels.csv"
    df.to_csv(out_csv, index=False)
    print(f"\n[Step 0] Labels saved to {out_csv}")
    print("\n[Step 0] ✓ Done. Proceed to 02_pilot.py for the auth pilot read.")
