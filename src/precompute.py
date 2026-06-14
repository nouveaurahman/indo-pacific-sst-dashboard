"""
src/precompute.py
Orchestrator script — runs the full pipeline end to end:
  1. Ingest raw ERSST files from Azure Blob (raw container)
  2. Compute SST anomalies against 1975-2014 baseline
  3. Compute Nino 3.4 index with ENSO classification
  4. Save outputs to Azure Blob (processed container)

Run this once after downloading raw data.
Dashboard reads only from processed container at runtime.

Usage:
    python -m src.precompute
"""

import time
from src.ingest import open_dataset
from src.anomaly import compute_anomaly, compute_nino34, save_to_blob


def main():
    t0 = time.time()
    print("=" * 55)
    print("  SST Dashboard — Precompute Pipeline")
    print("=" * 55)

    # ── Stage 1: Ingest ──────────────────────────────────────
    print("\n[1/4] Ingesting ERSST v5 from Azure Blob Storage...")
    t1 = time.time()
    ds = open_dataset(year_start=1975, year_end=2025, verbose=True)
    print(f"      Done in {time.time()-t1:.0f}s")

    # ── Stage 2: Anomaly computation ─────────────────────────
    print("\n[2/4] Computing SST anomalies (baseline 1975-2014)...")
    t2 = time.time()
    ds_anom = compute_anomaly(ds, verbose=True)
    print(f"      Done in {time.time()-t2:.0f}s")

    # ── Stage 3: Nino 3.4 index ──────────────────────────────
    print("\n[3/4] Computing Nino 3.4 index...")
    t3 = time.time()
    df_nino = compute_nino34(ds_anom, verbose=True)
    print(f"      Done in {time.time()-t3:.0f}s")

    # ── Stage 4: Save to blob ─────────────────────────────────
    print("\n[4/4] Saving outputs to processed container...")
    t4 = time.time()
    save_to_blob(ds_anom, df_nino, verbose=True)
    print(f"      Done in {time.time()-t4:.0f}s")

    # ── Summary ───────────────────────────────────────────────
    total = time.time() - t0
    print("\n" + "=" * 55)
    print(f"  Pipeline complete in {total:.0f}s ({total/60:.1f} min)")
    print("  Outputs in processed container:")
    print("    processed/ssta.zarr         — SST anomaly array")
    print("    processed/nino34_index.parquet — Nino 3.4 index")
    print("=" * 55)

    # ── Validation summary ────────────────────────────────────
    print("\nValidation:")
    print(f"  SSTA dims    : {dict(ds_anom['ssta'].sizes)}")
    print(f"  Nino34 rows  : {len(df_nino)}")
    print(f"  El Nino months : {(df_nino['enso_phase']=='El Nino').sum()}")
    print(f"  La Nina months : {(df_nino['enso_phase']=='La Nina').sum()}")
    print(f"  Peak Nino34  : "
          f"{df_nino['nino34_smooth'].max():.2f} C "
          f"({df_nino['nino34_smooth'].idxmax().strftime('%Y-%m')})")
    print(f"  Trough Nino34: "
          f"{df_nino['nino34_smooth'].min():.2f} C "
          f"({df_nino['nino34_smooth'].idxmin().strftime('%Y-%m')})")


if __name__ == "__main__":
    main()
