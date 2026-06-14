"""
src/download_ersst.py
Downloads all NOAA ERSST v5 monthly .nc files from 1975-2025
into Azure Blob Storage (container: raw).
Resume-safe — skips files already uploaded.
"""

import os
import requests
from pathlib import Path
from dotenv import load_dotenv
from azure.storage.blob import BlobServiceClient

load_dotenv()

CONN_STR      = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
CONTAINER     = "raw"
NOAA_BASE_URL = "https://www.ncei.noaa.gov/pub/data/cmb/ersst/v5/netcdf"
LOCAL_TEMP    = Path("/tmp/ersst_temp")
LOCAL_TEMP.mkdir(exist_ok=True)

YEARS  = range(1975, 2026)
MONTHS = range(1, 13)


def blob_exists(client, blob_name: str) -> bool:
    try:
        client.get_blob_client(container=CONTAINER, blob=blob_name).get_blob_properties()
        return True
    except Exception:
        return False


def download_and_upload(client, year: int, month: int) -> str:
    filename   = f"ersst.v5.{year}{month:02d}.nc"
    url        = f"{NOAA_BASE_URL}/{filename}"
    local_path = LOCAL_TEMP / filename

    if blob_exists(client, filename):
        return f"  SKIP  {filename}"

    r = requests.get(url, timeout=60)
    if r.status_code == 404:
        return f"  MISS  {filename} (not yet published)"
    r.raise_for_status()
    local_path.write_bytes(r.content)

    with open(local_path, "rb") as f:
        client.get_blob_client(container=CONTAINER, blob=filename).upload_blob(f, overwrite=True)

    local_path.unlink()
    return f"  UP    {filename} ({len(r.content)/1024:.0f} KB)"


def main():
    assert CONN_STR, "AZURE_STORAGE_CONNECTION_STRING not set in .env"
    client  = BlobServiceClient.from_connection_string(CONN_STR)
    total   = len(list(YEARS)) * 12
    done    = skipped = 0
    errors  = []

    print(f"Starting ERSST v5 download — {total} files (1975-2025)\n")

    for year in YEARS:
        for month in MONTHS:
            try:
                result = download_and_upload(client, year, month)
                print(result)
                if "SKIP" in result:
                    skipped += 1
                else:
                    done += 1
            except Exception as e:
                msg = f"  ERR   {year}{month:02d} — {e}"
                print(msg)
                errors.append(msg)

    print(f"\nDone. Uploaded: {done}  Skipped: {skipped}  Errors: {len(errors)}")
    if errors:
        print("\nFailed files:")
        for e in errors:
            print(e)

if __name__ == "__main__":
    main()
