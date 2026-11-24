"""Social Pulse demo server."""

from __future__ import annotations

import csv
import io
import json
import mimetypes
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).parent
WEB_DIR = ROOT / "web"
DEMO_CSV = ROOT / "data" / "sample_posts.csv"


def engagement(post: dict[str, object]) -> float:
    likes = float(post.get("likes", 0))
    comments = float(post.get("comments", 0))
    shares = float(post.get("shares", 0))
    followers = max(float(post.get("followers", 1)), 1)
    return ((likes + comments * 2 + shares * 3) / followers) * 100


def parse_posts(text: str) -> list[dict[str, object]]:
    reader = csv.DictReader(io.StringIO(text))
    required = {"date", "platform", "content_type", "caption", "likes", "comments", "shares", "followers"}
    if not reader.fieldnames or not required.issubset(set(reader.fieldnames)):
        raise ValueError("CSV needs date, platform, content_type, caption, likes, comments, shares, and followers")

    posts: list[dict[str, object]] = []
    for row in reader:
        try:
            post = {
                "date": row["date"].strip(),
                "platform": row["platform"].strip().title(),
                "content_type": row["content_type"].strip().title(),
                "caption": row["caption"].strip(),
                "likes": int(row["likes"]),
                "comments": int(row["comments"]),
                "shares": int(row["shares"]),
                "followers": int(row["followers"]),
            }
        except (KeyError, TypeError, ValueError) as error:
            raise ValueError("The CSV contains an invalid row") from error
        if min(post[key] for key in ("likes", "comments", "shares", "followers")) < 0:
            raise ValueError("Likes, comments, shares, and followers must be zero or greater")
        post["engagement"] = round(engagement(post), 2)
        posts.append(post)
    if not posts:
        raise ValueError("The CSV has no posts")
    return posts


def analyze(posts: list[dict[str, object]], platform: str = "All") -> dict[str, object]:
    if platform != "All":
        posts = [post for post in posts if post["platform"].lower() == platform.lower()]
    if not posts:
        raise ValueError("No posts found for that platform")

    ranked = sorted(posts, key=lambda post: float(post["engagement"]), reverse=True)
    average = sum(float(post["engagement"]) for post in posts) / len(posts)
    types: dict[str, list[float]] = {}
    platforms: dict[str, list[float]] = {}
    for post in posts:
        types.setdefault(str(post["content_type"]), []).append(float(post["engagement"]))
        platforms.setdefault(str(post["platform"]), []).append(float(post["engagement"]))

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

    return {
        "summary": {
            "posts": len(posts),
            "total_likes": sum(int(post["likes"]) for post in posts),
            "total_comments": sum(int(post["comments"]) for post in posts),
            "total_shares": sum(int(post["shares"]) for post in posts),
            "average_engagement": round(average, 2),
        },
        "top_posts": ranked[:5],
        "content_types": averages(types),
        "platforms": averages(platforms),
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
        self.end_headers()
        self.wfile.write(body)

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
        self.end_headers()
        self.wfile.write(content)

    def do_POST(self) -> None:
        if urlparse(self.path).path != "/api/analyze":
            self.send_error(404)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            text = self.rfile.read(length).decode("utf-8")
            data = json.loads(text)
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
