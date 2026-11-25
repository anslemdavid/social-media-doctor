import json
import sys
import threading
import unittest
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

sys.path.insert(0, str(Path(__file__).parents[1]))

import app


VALID_CSV = (
    "date,platform,content_type,caption,likes,comments,shares,followers\n"
    '2026-11-03,Instagram,Reel,"A useful post",100,20,10,1000\n'
)


class SocialPulseTests(unittest.TestCase):
    def test_parse_and_analyze_sample_data(self):
        posts = app.parse_posts(app.DEMO_CSV.read_text(encoding="utf-8"))
        report = app.analyze(posts)
        self.assertEqual(report["summary"]["posts"], 10)
        self.assertEqual(report["top_posts"][0]["engagement"], 23.52)
        self.assertEqual(len(report["top_posts"]), 5)
        self.assertEqual(report["available_platforms"], ["Instagram", "LinkedIn", "TikTok", "X"])
        self.assertTrue(report["content_types"])
        self.assertEqual(report["summary"]["followers"], 200000)
        self.assertEqual(report["best_time"]["label"], "6 PM–7 PM")
        self.assertEqual(report["best_time"]["posts"], 3)
        self.assertTrue(report["recommendations"])

    def test_engagement_rate_uses_all_interactions_and_followers(self):
        post = app.parse_posts(VALID_CSV)[0]
        self.assertEqual(post["engagement"], 13.0)
        self.assertIsNone(post["time"])

    def test_optional_post_time_is_analyzed_and_validated(self):
        csv_text = VALID_CSV.replace(
            "date,platform",
            "date,time,platform",
        ).replace(
            "2026-11-03,Instagram",
            "2026-11-03,18:30,Instagram",
        )
        report = app.analyze(app.parse_posts(csv_text))
        self.assertEqual(report["best_time"]["label"], "6 PM–7 PM")
        self.assertEqual(report["best_time"]["posts"], 1)

        with self.assertRaisesRegex(ValueError, "row 2 contains an invalid value"):
            app.parse_posts(csv_text.replace("18:30", "9:30"))

    def test_filter_platform(self):
        posts = app.parse_posts(app.DEMO_CSV.read_text(encoding="utf-8"))
        report = app.analyze(posts, "Instagram")
        self.assertEqual(report["summary"]["posts"], 3)
        self.assertEqual(report["summary"]["followers"], 50000)
        self.assertTrue(all(post["platform"] == "Instagram" for post in report["top_posts"]))
        self.assertEqual(report["available_platforms"], ["Instagram", "LinkedIn", "TikTok", "X"])

    def test_csv_accepts_bom_and_whitespace_in_headers(self):
        csv_text = "\ufeffdate, platform,content_type,caption,likes,comments,shares,followers\n" + VALID_CSV.split("\n", 1)[1]
        self.assertEqual(len(app.parse_posts(csv_text)), 1)

    def test_csv_rejects_missing_columns(self):
        with self.assertRaisesRegex(ValueError, "CSV needs"):
            app.parse_posts("date,platform\n2026-01-01,Instagram")

    def test_csv_rejects_invalid_date_and_nonpositive_followers(self):
        with self.assertRaisesRegex(ValueError, "row 2 contains an invalid value"):
            app.parse_posts(VALID_CSV.replace("2026-11-03", "not-a-date"))
        with self.assertRaisesRegex(ValueError, "followers must be greater than zero"):
            app.parse_posts(VALID_CSV.replace(",1000\n", ",0\n"))

    def test_csv_rejects_negative_counts_and_wrong_column_count(self):
        with self.assertRaisesRegex(ValueError, "cannot be negative"):
            app.parse_posts(VALID_CSV.replace(",100,20,10,1000", ",-1,20,10,1000"))
        with self.assertRaisesRegex(ValueError, "wrong number of columns"):
            app.parse_posts(VALID_CSV.rstrip() + ",unexpected\n")

    def test_csv_rejects_duplicate_headers_and_oversized_input(self):
        with self.assertRaisesRegex(ValueError, "must be unique"):
            app.parse_posts(VALID_CSV.replace("likes,comments", "likes,likes"))
        with self.assertRaisesRegex(ValueError, "no larger than 2 MB"):
            app.parse_posts(VALID_CSV + (" " * app.MAX_CSV_BYTES))

    def test_dashboard_serves_static_api_and_security_headers(self):
        server = app.create_server(port=0)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            base = f"http://127.0.0.1:{server.server_port}"
            with urlopen(base + "/") as response:
                page = response.read().decode("utf-8")
                self.assertEqual(response.status, 200)
                self.assertIn("Social Pulse", page)
                self.assertIn('id="timeline-chart"', page)
                self.assertIn('id="profile-form"', page)
                self.assertIn("Demo data is shown until you import your own account data.", page)
                self.assertEqual(response.headers["X-Content-Type-Options"], "nosniff")
                self.assertIn("frame-ancestors 'none'", response.headers["Content-Security-Policy"])
            with urlopen(base + "/api/analyze") as response:
                payload = json.loads(response.read())
                self.assertEqual(payload["summary"]["posts"], 10)
                self.assertEqual(payload["summary"]["followers"], 200000)
                self.assertEqual(payload["best_time"]["label"], "6 PM–7 PM")
                self.assertEqual(payload["available_platforms"], ["Instagram", "LinkedIn", "TikTok", "X"])
                self.assertEqual(len(payload["recommendations"]), 2)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)

    def test_upload_api_accepts_csv_and_rejects_non_object_json(self):
        server = app.create_server(port=0)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base = f"http://127.0.0.1:{server.server_port}/api/analyze"
        try:
            body = json.dumps({"csv": VALID_CSV, "platform": "Instagram"}).encode("utf-8")
            request = Request(base, data=body, headers={"Content-Type": "application/json"})
            with urlopen(request) as response:
                payload = json.loads(response.read())
                self.assertEqual(payload["summary"]["posts"], 1)
                self.assertEqual(payload["summary"]["average_engagement"], 13.0)

            request = Request(base, data=b"[]", headers={"Content-Type": "application/json"})
            with self.assertRaises(HTTPError) as error:
                urlopen(request)
            self.assertEqual(error.exception.code, 400)
            self.assertIn("JSON object", error.exception.read().decode("utf-8"))
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)

    def test_static_path_traversal_is_not_served(self):
        server = app.create_server(port=0)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with self.assertRaises(HTTPError) as error:
                urlopen(f"http://127.0.0.1:{server.server_port}/%2e%2e/app.py")
            self.assertEqual(error.exception.code, 404)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)


if __name__ == "__main__":
    unittest.main()
