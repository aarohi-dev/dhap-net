"""
pipeline/01_parse_labels.py
───────────────────────────
Parse the local redteam.txt file (already present at data/raw/redteam.txt)
and compute the slice window for flows.txt.

Usage:
    python pipeline/01_parse_labels.py

Outputs:
    data/raw/redteam_labels.csv
    reports/slice_window.json
"""

import sys, json, io
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from configs.config import (
    REDTEAM_TXT, DATA_DIR, REPORTS_DIR, LEADN_DAYS
)
import pandas as pd


def parse_redteam(path: Path) -> pd.DataFrame:
    records = []
    bad = 0
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            parts = line.strip().split(",")
            if len(parts) < 4:
                bad += 1
                continue
            try:
                t = int(parts[0])
            except ValueError:
                bad += 1
                continue
            records.append({"time": t, "user": parts[1],
                             "src": parts[2], "dst": parts[3]})
    df = pd.DataFrame(records)
    print(f"[Labels] Parsed {len(df):,} red-team events, {bad} malformed lines")
    return df


def compute_slice(df: pd.DataFrame) -> dict:
    t_first = int(df["time"].min())
    t_last  = int(df["time"].max())
    t_start = max(t_first - LEADN_DAYS * 86400, 0)
    t_end   = t_last + 3600

    info = {
        "t_first_redteam": t_first,
        "t_last_redteam":  t_last,
        "t_start":         t_start,
        "t_end":           t_end,
        "lead_in_days":    LEADN_DAYS,
        "slice_days":      (t_end - t_start) / 86400,
        "rt_events":       len(df),
        "rt_hosts_compromised": int(df["dst"].nunique()),
        "rt_footholds":    int(
            len(set(df["src"].unique()) - set(df["dst"].unique()))
        ),
    }

    print("\n── Slice window ──────────────────────────────────────────────")
    print(f"  First red-team event : {t_first:,} s  (day {t_first//86400})")
    print(f"  Last  red-team event : {t_last:,} s  (day {t_last//86400})")
    print(f"  Lead-in              : {LEADN_DAYS} days")
    print(f"  t_start              : {t_start:,} s  (day {t_start//86400})")
    print(f"  t_end                : {t_end:,} s  (day {t_end//86400})")
    print(f"  Slice duration       : {info['slice_days']:.1f} days")
    print(f"  Compromised hosts    : {info['rt_hosts_compromised']}")
    print(f"  Foothold hosts       : {info['rt_footholds']}")

    slice_file = REPORTS_DIR / "slice_window.json"
    with open(slice_file, "w") as f:
        json.dump(info, f, indent=2)
    print(f"\n[Labels] Slice window --> {slice_file}")
    return info


def main():
    if not REDTEAM_TXT.exists():
        sys.exit(f"[ERROR] redteam.txt not found at {REDTEAM_TXT}")

    print(f"[Labels] Parsing {REDTEAM_TXT}  ({REDTEAM_TXT.stat().st_size:,} bytes)")
    df = parse_redteam(REDTEAM_TXT)

    df["day"]  = df["time"] // 86400
    df["hour"] = df["time"] // 3600

    print("\n── Red-team statistics ───────────────────────────────────────")
    print(f"  Events total       : {len(df):,}")
    print(f"  Distinct users     : {df['user'].nunique():,}")
    print(f"  Distinct src hosts : {df['src'].nunique():,}")
    print(f"  Distinct dst hosts : {df['dst'].nunique():,}")
    per_day = df.groupby("day").size()
    for day, n in per_day.items():
        print(f"  Day {day:3d}: {n:4d} events")

    info = compute_slice(df)

    out_csv = DATA_DIR / "redteam_labels.csv"
    df.to_csv(out_csv, index=False)
    print(f"[Labels] Labels saved --> {out_csv}")
    print("\n[Labels] OK Done.  Next: python pipeline/02_etl_flows.py")


if __name__ == "__main__":
    main()
