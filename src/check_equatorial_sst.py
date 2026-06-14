import sys
sys.path.insert(0, '.')
from src.ingest import open_dataset

ds = open_dataset(verbose=True)

# Equatorial Pacific — should show ~28-30°C for Jan 2000 (post El Niño peak)
eq_sst = ds["sst"].sel(
    time="2000-01",
    lat=slice(-5, 5),
    lon=slice(180, 270)
).values

import numpy as np
print(f"\nEquatorial Pacific SST (Jan 2000):")
print(f"  Mean : {np.nanmean(eq_sst):.2f} °C")
print(f"  Max  : {np.nanmax(eq_sst):.2f} °C")
print(f"  Min  : {np.nanmin(eq_sst):.2f} °C")