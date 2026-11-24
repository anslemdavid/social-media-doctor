# Social Pulse

A polished, offline-friendly social media analytics dashboard built for a final-project demo.

## Run

```powershell
python app.py
```

Open http://127.0.0.1:8080/

## Features

- Portfolio-ready dashboard with dark editorial design
- Top post ranking and engagement rate calculations
- Platform and content-type comparisons
- Timeline visualization
- CSV upload for real analysis
- Sample data that works without API keys or internet access
- Responsive layout and accessible controls

## CSV format

```text
date,platform,content_type,caption,likes,comments,shares,followers
2026-11-03,Instagram,Reel,Your post caption,8200,460,710,50000
```

## Test

```powershell
python -m unittest discover -s tests -v
```
