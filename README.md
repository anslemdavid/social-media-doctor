# Social Pulse

**A local-first social media analytics dashboard for understanding what content resonates.**

Social Pulse turns social media post exports into a clear, interactive report: compare engagement by platform and content type, find your strongest posts, discover a promising posting window, and get practical next steps. It runs locally, includes fictional sample data, and needs no API keys or third-party Python packages.

## Features

- At-a-glance engagement rate, likes, comments, and shares
- Latest follower counts, strongest content formats, and data-based recommendations
- Best-performing posting hour when the CSV includes post times
- Profile-link recognition for Instagram, TikTok, LinkedIn, X, YouTube, Facebook, and Threads
- Platform filtering and automatic date-range reporting
- Engagement timeline, content-type comparison, and ranked top posts
- CSV import with validation and clear row-level errors
- CSV export of the five highest-engagement posts
- Responsive dashboard, light/dark theme toggle, and keyboard-accessible controls
- Imported data is processed in memory and not saved or sent to a third party

Pasting a profile link identifies the platform; it does **not** fetch account analytics. The dashboard starts with fictional demo data and hides those charts after a profile is submitted, until you import real data. Social Pulse does not scrape profiles or connect to social networks. Choose **Import analytics CSV** and upload an export you own using the columns below to review real performance; the link will then filter the imported report by platform.

## Preview

Start the app and open <http://127.0.0.1:8080/> to explore the dashboard with the included sample dataset.

## Quick start

**Requirements:** Python 3.11 or newer.

```powershell
cd social_pulse
python app.py
```

Open <http://127.0.0.1:8080/> in your browser. Stop the local server with `Ctrl+C`.

## Import your data

Choose **Import CSV** and upload a UTF-8 CSV file up to 2 MB. Include these columns:

| Column | Meaning | Example |
| --- | --- | --- |
| `date` | Post date in `YYYY-MM-DD` format | `2026-11-03` |
| `time` | **Optional.** Post time in 24-hour `HH:MM` format | `18:30` |
| `platform` | Social platform name | `Instagram` |
| `content_type` | Format of the post | `Reel` |
| `caption` | Post text or a short description | `Behind the scenes` |
| `likes` | Number of likes (zero or greater) | `8200` |
| `comments` | Number of comments (zero or greater) | `460` |
| `shares` | Number of shares (zero or greater) | `710` |
| `followers` | Follower count for the account (greater than zero) | `50000` |

Example:

```csv
date,time,platform,content_type,caption,likes,comments,shares,followers
2026-11-03,18:30,Instagram,Reel,"Behind the scenes from our latest campaign",8200,460,710,50000
```

## Metric definition

**Engagement rate per post** is calculated as:

```text
(likes + comments + shares) / followers * 100
```

The dashboard's average engagement rate is the arithmetic mean of the per-post rates in the current selection. This is a follower-based rate, not impressions-based reach or a platform-reported metric.

The best-time insight groups posts by hour and compares their average engagement. Recommendations are heuristics based only on the supplied posts; they are suggestions to test, not guarantees. “Followers tracked” sums the latest follower count seen for each platform in the selected data.

## Run the tests

The project uses only the Python standard library:

```powershell
python -m unittest discover -s tests -v
```

## Project layout

```text
app.py                  HTTP server, CSV validation, and analytics
data/sample_posts.csv   Fictional demo dataset
tests/test_app.py       Unit and HTTP integration tests
web/                    Dashboard HTML, CSS, and JavaScript
```

## Privacy and deployment

The server binds to `127.0.0.1` by default. Uploaded CSV data is analyzed in memory and is not written to disk or sent to a third-party service. The included sample data is fictional.

This is a portfolio/demo application, not a production social network integration. It has no authentication, database, or platform API connections; do not expose it to a public network or upload confidential data to a shared machine. Real account-link analytics would require authorized platform APIs and account-owner consent.

## License

Distributed under the MIT License. See [LICENSE](LICENSE).
