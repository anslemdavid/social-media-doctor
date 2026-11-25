"""Social Pulse demo server."""

from __future__ import annotations

import csv
import io
import json
import mimetypes
from datetime import date, datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).parent
WEB_DIR = ROOT / "web"
DEMO_CSV = ROOT / "data" / "sample_posts.csv"
MAX_CSV_BYTES = 2 * 1024 * 1024
MAX_REQUEST_BYTES = MAX_CSV_BYTES * 6 + 4096
REQUIRED_COLUMNS = {
    "date",
    "platform",
    "content_type",
    "caption",
    "likes",
    "comments",
    "shares",
    "followers",
}


def engagement(post: dict[str, object]) -> float:
    likes = float(post.get("likes", 0))
    comments = float(post.get("comments", 0))
    shares = float(post.get("shares", 0))
    followers = float(post.get("followers", 0))
    if followers <= 0:
        raise ValueError("Followers must be greater than zero")
    return ((likes + comments + shares) / followers) * 100


def parse_posts(text: str) -> list[dict[str, object]]:
    text = text.removeprefix("\ufeff")
    if len(text.encode("utf-8")) > MAX_CSV_BYTES:
        raise ValueError("CSV must be no larger than 2 MB")
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise ValueError("CSV needs a header row")
    reader.fieldnames = [name.strip() for name in reader.fieldnames]
    if len(set(reader.fieldnames)) != len(reader.fieldnames):
        raise ValueError("CSV column names must be unique")
    if not REQUIRED_COLUMNS.issubset(set(reader.fieldnames)):
        raise ValueError("CSV needs date, platform, content_type, caption, likes, comments, shares, and followers")

    posts: list[dict[str, object]] = []
    for row in reader:
        row_number = reader.line_num
        if None in row or any(value is None for value in row.values()):
            raise ValueError(f"CSV row {row_number} has the wrong number of columns")
        try:
            post_date = row["date"].strip()
            if date.fromisoformat(post_date).isoformat() != post_date:
                raise ValueError
            platform = row["platform"].strip()
            content_type = row["content_type"].strip()
            caption = row["caption"].strip()
            if not platform or not content_type or not caption:
                raise ValueError
            post = {
                "date": post_date,
                "platform": platform,
                "content_type": content_type,
                "caption": caption,
                "likes": int(row["likes"]),
                "comments": int(row["comments"]),
                "shares": int(row["shares"]),
                "followers": int(row["followers"]),
            }
            post_time = row.get("time", "").strip()
            normalized_time = datetime.strptime(post_time, "%H:%M").strftime("%H:%M") if post_time else None
            if normalized_time is not None and normalized_time != post_time:
                raise ValueError
            post["time"] = normalized_time
        except (KeyError, TypeError, ValueError) as error:
            raise ValueError(f"CSV row {row_number} contains an invalid value") from error
        if min(post[key] for key in ("likes", "comments", "shares")) < 0:
            raise ValueError(f"CSV row {row_number}: likes, comments, and shares cannot be negative")
        if post["followers"] <= 0:
            raise ValueError(f"CSV row {row_number}: followers must be greater than zero")
        post["engagement"] = round(engagement(post), 2)
        posts.append(post)
    if not posts:
        raise ValueError("The CSV has no posts")
    return posts


def analyze(posts: list[dict[str, object]], platform: str = "All") -> dict[str, object]:
    available_platforms = sorted(
        {str(post["platform"]) for post in posts},
        key=str.casefold,
    )
    if platform != "All":
        posts = [post for post in posts if post["platform"].lower() == platform.lower()]
    if not posts:
        raise ValueError("No posts found for that platform")

    ranked = sorted(posts, key=lambda post: float(post["engagement"]), reverse=True)
    average = sum(float(post["engagement"]) for post in posts) / len(posts)
    total_likes = sum(int(post["likes"]) for post in posts)
    total_comments = sum(int(post["comments"]) for post in posts)
    total_shares = sum(int(post["shares"]) for post in posts)
    total_interactions = total_likes + total_comments + total_shares
    types: dict[str, list[float]] = {}
    platforms: dict[str, list[float]] = {}
    times: dict[int, list[float]] = {}
    latest_followers: dict[str, tuple[str, int]] = {}
    for post in posts:
        types.setdefault(str(post["content_type"]), []).append(float(post["engagement"]))
        platforms.setdefault(str(post["platform"]), []).append(float(post["engagement"]))
        if post["time"] is not None:
            hour = int(str(post["time"]).split(":")[0])
            times.setdefault(hour, []).append(float(post["engagement"]))
        name = str(post["platform"])
        current = latest_followers.get(name)
        if current is None or str(post["date"]) >= current[0]:
            latest_followers[name] = (str(post["date"]), int(post["followers"]))

    def averages(groups: dict[str, list[float]]) -> list[dict[str, object]]:
        result = [
            {
                "name": name,
                "engagement": round(sum(values) / len(values), 2),
                "posts": len(values),
            }
            for name, values in groups.items()
        ]
        return sorted(result, key=lambda item: float(item["engagement"]), reverse=True)

    best_time = None
    if times:
        best_hour = max(times, key=lambda hour: sum(times[hour]) / len(times[hour]))
        next_hour = (best_hour + 1) % 24
        start_label = f"{best_hour % 12 or 12} {'AM' if best_hour < 12 else 'PM'}"
        end_label = f"{next_hour % 12 or 12} {'AM' if next_hour < 12 else 'PM'}"
        best_time = {
            "label": f"{start_label}–{end_label}",
            "engagement": round(sum(times[best_hour]) / len(times[best_hour]), 2),
            "posts": len(times[best_hour]),
        }

    content_averages = averages(types)
    recommendations: list[dict[str, str]] = []
    if content_averages:
        best_format = content_averages[0]
        recommendations.append({
            "title": f"Lean into {best_format['name']} posts",
            "detail": (
                f"They lead your formats at {best_format['engagement']}% average engagement "
                f"across {best_format['posts']} post(s)."
            ),
        })
    if average < 2:
        recommendations.append({
            "title": "Give people a reason to respond",
            "detail": "Try a stronger opening, one clear question, and a direct invitation to comment or share.",
        })
    elif total_comments / max(1, total_interactions) < 0.1:
        comment_share = round(total_comments / max(1, total_interactions) * 100, 1)
        recommendations.append({
            "title": "Invite more conversation",
            "detail": (
                f"Comments make up {comment_share}% of interactions. "
                "Test a specific question or prompt that gives followers an easy way to reply."
            ),
        })
    elif best_time:
        recommendations.append({
            "title": f"Test the {best_time['label']} time slot",
            "detail": (
                f"Your posts in this hour average {best_time['engagement']}% engagement. "
                "Repeat the test before treating it as a trend."
            ),
        })
    else:
        recommendations.append({
            "title": "Add post times to your export",
            "detail": "Include a time column in 24-hour HH:MM format to discover when your audience responds.",
        })

    return {
        "summary": {
            "posts": len(posts),
            "total_likes": total_likes,
            "total_comments": total_comments,
            "total_shares": total_shares,
            "average_engagement": round(average, 2),
            "followers": sum(value[1] for value in latest_followers.values()),
        },
        "available_platforms": available_platforms,
        "top_posts": ranked[:5],
        "content_types": content_averages,
        "platforms": averages(platforms),
        "best_time": best_time,
        "recommendations": recommendations,
        "timeline": sorted(
            [
                {
                    "date": post["date"],
                    "engagement": float(post["engagement"]),
                    "platform": post["platform"],
                }
                for post in posts
            ],
            key=lambda item: str(item["date"]),
        ),
    }


class SocialPulseHandler(BaseHTTPRequestHandler):
    def _json(self, status: int, payload: dict[str, object]) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self._security_headers()
        self.end_headers()
        self.wfile.write(body)

    def _security_headers(self) -> None:
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline' "
            "https://fonts.googleapis.com; font-src https://fonts.gstatic.com; "
            "connect-src 'self'; img-src 'self' data:; object-src 'none'; "
            "base-uri 'self'; frame-ancestors 'none'",
        )

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/analyze":
            try:
                platform = parse_qs(parsed.query).get("platform", ["All"])[0]
                posts = parse_posts(DEMO_CSV.read_text(encoding="utf-8"))
                self._json(200, analyze(posts, platform))
            except (OSError, ValueError) as error:
                self._json(400, {"error": str(error)})
            return

        path = WEB_DIR / ("index.html" if parsed.path in ("", "/") else parsed.path.lstrip("/"))
        if not path.resolve().is_relative_to(WEB_DIR.resolve()) or not path.is_file():
            self.send_error(404)
            return
        content = path.read_bytes()
        mimetype = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        self.send_response(200)
        self.send_header("Content-Type", mimetype)
        self.send_header("Content-Length", str(len(content)))
        self._security_headers()
        self.end_headers()
        self.wfile.write(content)

    def do_POST(self) -> None:
        if urlparse(self.path).path != "/api/analyze":
            self.send_error(404)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length < 0 or length > MAX_REQUEST_BYTES:
                raise ValueError("Request body must be no larger than 2 MB")
            text = self.rfile.read(length).decode("utf-8")
            data = json.loads(text)
            if not isinstance(data, dict):
                raise ValueError("Request body must be a JSON object")
            platform = str(data.get("platform", "All"))
            if "csv" not in data:
                raise ValueError("CSV text is required")
            posts = parse_posts(str(data["csv"]))
            self._json(200, analyze(posts, platform))
        except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
            self._json(400, {"error": str(error)})

    def log_message(self, format: str, *args: object) -> None:
        print(f"{self.address_string()} - {format % args}")


def create_server(host: str = "127.0.0.1", port: int = 8080) -> ThreadingHTTPServer:
    return ThreadingHTTPServer((host, port), SocialPulseHandler)


def main() -> None:
    server = create_server()
    print("Social Pulse is running at http://127.0.0.1:8080/")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nSocial Pulse stopped.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
