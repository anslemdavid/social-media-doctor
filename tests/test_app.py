import sys
import threading
import unittest
from pathlib import Path
from urllib.request import urlopen

sys.path.insert(0, str(Path(__file__).parents[1]))

import app


class SocialPulseTests(unittest.TestCase):
    def test_parse_and_analyze_sample_data(self):
        posts = app.parse_posts(app.DEMO_CSV.read_text(encoding="utf-8"))
        report = app.analyze(posts)
        self.assertEqual(report["summary"]["posts"], 10)
        self.assertGreater(report["summary"]["average_engagement"], 0)
        self.assertEqual(len(report["top_posts"]), 5)
        self.assertTrue(report["content_types"])

    def test_filter_platform(self):
        posts = app.parse_posts(app.DEMO_CSV.read_text(encoding="utf-8"))
        report = app.analyze(posts, "Instagram")
        self.assertEqual(report["summary"]["posts"], 3)
        self.assertTrue(all(post["platform"] == "Instagram" for post in report["top_posts"]))

    def test_invalid_csv_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "CSV needs"):
            app.parse_posts("date,platform\n2026-01-01,Instagram")

    def test_dashboard_serves_static_and_api(self):
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
            with urlopen(base + "/api/analyze") as response:
                import json
                payload = json.loads(response.read())
                self.assertEqual(payload["summary"]["posts"], 10)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)


if __name__ == "__main__":
    unittest.main()
