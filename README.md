cat > README.md << 'EOF'
# 🌊 Indo-Pacific SST Dashboard

Interactive explorer for 51 years of Indo-Pacific sea surface
temperature data (1975–2025), built as a portfolio project in
the context of the forecasted 2026 El Niño event.

## Features
- Monthly SST anomaly maps using Cartopy (1975–2025)
- Niño 3.4 index time series with ENSO event shading
- Highlights major El Niño events: 1982–83, 1997–98, 2015–16, 2023–24
- Year/month slider for scrubbing through time

## Data
- **Source**: NOAA ERSST v5 (2° × 2° monthly gridded SST)
- **Region**: Indo-Pacific (20°E–290°E, 60°S–60°N)
- **Baseline**: 1975–2014 climatological mean
- **ENSO index**: Niño 3.4 region (5°S–5°N, 170°W–120°W)

## Tech Stack
Python · xarray · Cartopy · Matplotlib · Plotly · Streamlit · Azure Blob Storage

## Live Demo
[Launch Dashboard](https://share.streamlit.io)

## Project Structure
\`\`\`
sst-dashboard/
  src/
    ingest.py          # ERSST download + xarray ingestion
    anomaly.py         # SST anomaly computation + Niño 3.4 index
    precompute.py      # Pipeline orchestrator
  dashboard/
    app.py             # Streamlit main app
    map_panel.py       # Cartopy map renderer
    chart_panel.py     # Plotly Niño 3.4 chart
\`\`\`

## Author
(Abdul Rahman)
EOF

git add README.md
git commit -m "Add README"
git push
