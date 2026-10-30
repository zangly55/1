"""看板服务测试：路由、JSON 结构、反馈回传校验。"""
from __future__ import annotations

import json
import os
import tempfile
import unittest
import urllib.error
import urllib.request

import helpers

from cvalarm.locator import Calibration, Localizer
from cvalarm.pipeline import Pipeline
from cvalarm.rules import Rule, RuleSet
from cvalarm.server import serve_background


def ruleset() -> RuleSet:
    return RuleSet(ruleset_id="srv", version_label="srv1", policy={}, created_at="",
                   rules=[Rule("R1", ["UNAUTHORIZED_INTRUSION"],
                               {"all": [{"field": "dwell_seconds", "op": ">=", "value": 10}]},
                               "alarm", priority=80, norm_ref="细则", description="滞留")])


class TestServer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="cvalarm-srv-")
        cls.cfg = helpers.default_config()
        cls.cfg.set("runtime.state_dir", cls.tmp)
        cls.cfg.set("stage3.authorization_file", os.path.join(cls.tmp, "none.json"))
        localizer = Localizer(cls.cfg, calibration=Calibration(
            version="cal", tau_reject=0.1, tau_confirm=0.3, hard_negative_windows=40))
        pipeline = Pipeline(cls.cfg, helpers.TinySource(hours=0.04), ruleset=ruleset(),
                            localizer=localizer, persist=True,
                            out_dir=os.path.join(cls.tmp, "run"))
        pipeline.run()
        cls.run_dir = pipeline.out_dir
        cls.httpd, cls.thread = serve_background(cls.run_dir, cls.cfg,
                                                 port=0)
        cls.port = cls.httpd.server_address[1]

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()

    def _get(self, path: str, expect_json: bool = True):
        url = f"http://127.0.0.1:{self.port}{path}"
        with urllib.request.urlopen(url, timeout=10) as resp:
            body = resp.read().decode("utf-8")
            if expect_json:
                return resp.status, json.loads(body)
            return resp.status, body

    def test_health(self):
        status, data = self._get("/api/health")
        self.assertEqual(status, 200)
        self.assertTrue(data["ok"])
        self.assertIn("metrics.json", data["files"])

    def test_index_html(self):
        status, body = self._get("/", expect_json=False)
        self.assertEqual(status, 200)
        self.assertIn("持续视频监控", body)
        self.assertIn("/api/run", body)

    def test_api_run_payload(self):
        status, data = self._get("/api/run")
        self.assertEqual(status, 200)
        for key in ("meta", "metrics", "cost", "alarms", "events", "rules", "topologies"):
            self.assertIn(key, data)
        self.assertTrue(data["alarms"])

    def test_api_metrics_and_cost(self):
        status, metrics = self._get("/api/metrics")
        self.assertEqual(status, 200)
        self.assertIn("event_recall", metrics)
        status, cost = self._get("/api/cost")
        self.assertEqual(status, 200)
        self.assertIn("components_money_per_camera_hour", cost)

    def test_api_rules(self):
        status, data = self._get("/api/rules")
        self.assertEqual(status, 200)
        self.assertIn("active", data)
        self.assertIn("ledger", data)

    def test_unknown_route(self):
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            self._get("/api/nope")
        self.assertEqual(ctx.exception.code, 404)

    def test_feedback_post_validation(self):
        url = f"http://127.0.0.1:{self.port}/api/feedback"
        meta = helpers.read_json_file(os.path.join(self.run_dir, "run_meta.json"))
        with open(os.path.join(self.run_dir,"alarms.jsonl"), encoding="utf-8") as handle:
            alarm = next(json.loads(line) for line in handle if json.loads(line)["status"] in ("confirmed","deferred"))
        payload = {"alarm_id": alarm["alarm_id"], "run_id": meta["run_id"],
                   "verdict": "dismiss", "reason_code": "OTHER"}
        req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"),
                                     method="POST",
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            self.assertEqual(resp.status, 200)
            body = json.loads(resp.read().decode("utf-8"))
            self.assertTrue(body["ok"])

        bad = {"alarm_id": "A2", "verdict": "dismiss"}
        req = urllib.request.Request(url, data=json.dumps(bad).encode("utf-8"),
                                     method="POST",
                                     headers={"Content-Type": "application/json"})
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            urllib.request.urlopen(req, timeout=10)
        self.assertEqual(ctx.exception.code, 400)


class TestMediaReplay(unittest.TestCase):
    """证据回放：未配置媒体时 404，配置后必须支持 HTTP Range（浏览器拖动进度条）。"""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="cvalarm-media-")
        cls.video = os.path.join(cls.tmp, "cam01.mp4")
        with open(cls.video, "wb") as fh:
            fh.write(bytes(range(100)) * 2)  # 200 字节
        cls.run_dir = os.path.join(cls.tmp, "run")
        os.makedirs(cls.run_dir, exist_ok=True)
        cls.cfg = helpers.default_config()
        cls.cfg.set("runtime.state_dir", cls.tmp)
        cls.cfg.set("deployment.media.root", cls.tmp)
        cls.cfg.set("deployment.media.cameras", {"CAM-01": "cam01.mp4"})
        cls.httpd, cls.thread = serve_background(cls.run_dir, cls.cfg, port=0)
        cls.port = cls.httpd.server_address[1]

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()

    def _request(self, path, headers=None):
        url = f"http://127.0.0.1:{self.port}{path}"
        req = urllib.request.Request(url, headers=headers or {})
        return urllib.request.urlopen(req, timeout=10)

    def test_full_get(self):
        with self._request("/media/CAM-01") as resp:
            self.assertEqual(resp.status, 200)
            self.assertEqual(resp.headers["Accept-Ranges"], "bytes")
            self.assertEqual(resp.headers["Content-Type"], "video/mp4")
            self.assertEqual(len(resp.read()), 200)

    def test_range_request(self):
        with self._request("/media/CAM-01", {"Range": "bytes=10-19"}) as resp:
            self.assertEqual(resp.status, 206)
            self.assertEqual(resp.headers["Content-Range"], "bytes 10-19/200")
            self.assertEqual(len(resp.read()), 10)

    def test_unknown_camera_404(self):
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            self._request("/media/CAM-99")
        self.assertEqual(ctx.exception.code, 404)

    def test_suffix_range(self):
        with self._request("/media/CAM-01", {"Range": "bytes=-10"}) as resp:
            self.assertEqual(resp.status, 206)
            self.assertEqual(resp.headers["Content-Range"], "bytes 190-199/200")


if __name__ == "__main__":
    unittest.main()
