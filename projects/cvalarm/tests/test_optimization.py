"""Regression coverage for the approved optimization scope."""
import copy
import io
import json
import tempfile
import unittest
import urllib.request
import urllib.error
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path
import helpers
from cvalarm.cli import main
from cvalarm.config import Config
from cvalarm.rules import RuleRegistry
from cvalarm.pipeline import Pipeline
from cvalarm.metrics import evaluate
from cvalarm.types import GtEvent, AlarmRecord
from cvalarm.types import Candidate, Stage2Result
from cvalarm.verifier import LLMVerifier, RuleBasedVerifier, AuthorizationBook
from cvalarm.rules import RuleEngine
from cvalarm.source import JsonlSource, write_frames_jsonl
from cvalarm.locator import calibrate, save_calibration
from cvalarm.server import serve_background

class OptimizationTests(unittest.TestCase):
    def test_short_demo_does_not_evaluate_unobserved_future_events(self):
        from cvalarm.source import build_demo, build_v1
        for factory in (build_demo,build_v1):
            run = Pipeline(self.cfg,factory(hours=.01),persist=False).run()
            self.assertEqual(run.metrics["events"],0)
            self.assertLessEqual(run.meta["frames"],144)

    def test_reliability_does_not_count_deferred_or_wrong_event(self):
        from cvalarm.reliability import conditional_recall
        events = [GtEvent("E", "C", "X", 0, 100, "R")]
        candidate = Candidate("C1", "C", 1, "R", "X", 0, 50, 50, 45)
        stage2 = Stage2Result("EVENT", (0,50), .9,.9,.55,.25,.65)
        alarm = AlarmRecord("A","C1","C",1,"R","X",45,50,51,"deferred","EVENT")
        result = conditional_recall(events,[candidate],{"C1":stage2},[alarm])
        self.assertEqual(result["end_to_end_recall_observed"],0)
        candidate.event_class = "Y"
        result = conditional_recall(events,[candidate],{"C1":stage2},[])
        self.assertEqual(result["p1_prefilter"],0)

    def test_localizer_service_receives_evidence_and_failure_is_explicit(self):
        from cvalarm.locator import Localizer
        from tests.test_locator import candidate, features
        seen = []
        bad_response = []
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args): pass
            def do_POST(handler):
                body = json.loads(handler.rfile.read(int(handler.headers["Content-Length"])))
                seen.append(body)
                data = json.dumps(bad_response[0] if bad_response else {"scores":[.8]*len(body["bins"])}).encode()
                handler.send_response(200); handler.end_headers(); handler.wfile.write(data)
        server = ThreadingHTTPServer(("127.0.0.1",0),Handler)
        threading.Thread(target=server.serve_forever,daemon=True).start()
        self.addCleanup(server.server_close); self.addCleanup(server.shutdown)
        manifest=self.root/"frames.json"; (self.root/"frame.jpg").write_bytes(b"\xff\xd8\xff\xd9")
        manifest.write_text(json.dumps({"CAM-T":[{"ts":1,"path":"frame.jpg","frame_idx":1}]}))
        self.cfg.set("stage3.vlm.frames_manifest",str(manifest))
        self.cfg.set("stage2.scorer.kind","http")
        self.cfg.set("stage2.scorer.endpoint",f"http://127.0.0.1:{server.server_address[1]}")
        result=Localizer(self.cfg).run(candidate(), features(persons=1,score=.9))
        self.assertEqual(result.raw_score,.8)
        self.assertTrue(seen[0]["frames"])
        bad_response.append([])
        malformed = Localizer(self.cfg).run(candidate(), features(persons=1,score=.9))
        self.assertEqual(malformed.decision,"SYSTEM_ERROR")
        self.cfg.set("stage2.scorer.endpoint","http://127.0.0.1:1/unavailable")
        failed = Localizer(self.cfg).run(candidate(), features(persons=1,score=.9))
        self.assertEqual(failed.decision,"SYSTEM_ERROR")
        self.assertIn("scorer_error",failed.validity)

    def test_dashboard_feedback_is_scoped_and_idempotent(self):
        self.cfg.set("feedback.reason_codes",["CUSTOM"])
        (self.root/"video.mp4").write_bytes(b"test-video-bytes")
        self.cfg.set("deployment.media",{"root":str(self.root),"cameras":{"CAM-T":"video.mp4"}})
        run = Pipeline(self.cfg, helpers.TinySource(), out_dir=str(self.root/"run")).run()
        httpd, thread = serve_background(str(self.root/"run"), Config.load(), port=0)
        self.addCleanup(httpd.server_close)
        self.addCleanup(httpd.shutdown)
        url = f"http://127.0.0.1:{httpd.server_address[1]}"
        payload = {"alarm_id":run.alarms[0]["alarm_id"],"run_id":run.meta["run_id"],
                   "verdict":"dismiss","reason_code":"CUSTOM"}
        def post(body):
            req = urllib.request.Request(url+"/api/feedback",json.dumps(body).encode(),
                                         headers={"Content-Type":"application/json"})
            with urllib.request.urlopen(req) as resp:
                return json.load(resp)
        post(payload); post(payload)
        with urllib.request.urlopen(url+"/api/feedback") as resp:
            entries = json.load(resp)
        self.assertEqual(len(entries),1)
        self.assertEqual(entries[0]["run_id"],run.meta["run_id"])
        with urllib.request.urlopen(url+"/media/CAM-T") as resp:
            self.assertEqual(resp.read(),b"test-video-bytes")
        with self.assertRaises(urllib.error.HTTPError):
            post({**payload, "run_id":"another-run"})

    def test_frozen_test_rejects_changed_rule_contents(self):
        args = ["test-report", "--hours", "3", "--no-report",
                "--state-dir", str(self.root/"state"), "--out", str(self.root/"run")]
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            self.assertEqual(main(args), 0)
        rules = RuleRegistry(self.cfg).active().to_dict()
        rules["description"] = "changed rules"
        changed = self.root/"changed.json"
        changed.write_text(json.dumps(rules), encoding="utf-8")
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            self.assertNotEqual(main(args + ["--rules", str(changed)]), 0)

    def test_runs_keep_config_and_unique_alarm_identity(self):
        first = Pipeline(self.cfg, helpers.TinySource(), persist=False).run()
        second = Pipeline(self.cfg, helpers.TinySource(), persist=False).run()
        self.assertIn("effective_config", first.meta)
        self.assertIn("ruleset_snapshot", first.meta)
        self.assertNotEqual(first.meta["run_id"], second.meta["run_id"])
        self.assertFalse({a["alarm_id"] for a in first.alarms} & {a["alarm_id"] for a in second.alarms})
        self.assertEqual(first.alarms[0]["latency"]["measurement_kind"], "simulation")

    def test_calibration_cannot_be_reused_after_scorer_change(self):
        source = helpers.TinySource()
        Pipeline(self.cfg, source, persist=False)  # bind input/scoring identity
        save_calibration(self.cfg, calibrate([.01]*40, 20))
        valid = Pipeline(self.cfg, source, persist=False).run()
        self.assertTrue(valid.meta["calibration"]["is_ok"])
        self.cfg.set("stage2.weights.roi_occupancy", .9)
        changed = Pipeline(self.cfg, source, persist=False).run()
        self.assertFalse(changed.meta["calibration"]["is_ok"])
        self.assertEqual(changed.meta["calibration"]["tau_confirm"],self.cfg.get("stage2.tau_confirm"))
        self.assertEqual(changed.meta["calibration"]["tau_reject"],self.cfg.get("stage2.tau_reject"))

    def test_unlabelled_replay_has_no_event_accuracy_claim(self):
        source = helpers.TinySource()
        frames, cameras = self.root/"frames.jsonl", self.root/"cameras.json"
        write_frames_jsonl(source, str(frames))
        cameras.write_text(json.dumps({"cameras":[c.to_dict() for c in source.cameras]}), encoding="utf-8")
        result = Pipeline(self.cfg, JsonlSource(str(frames), str(cameras)), persist=False).run()
        self.assertFalse(result.metrics["ground_truth_available"])
        self.assertIsNone(result.metrics["false_alarms_per_camera_hour"])
        self.assertIsNone(result.metrics["event_recall"])
        self.assertTrue(all(s["event_in_window"] is None for s in result.audit_samples))
        self.assertTrue(all(a["status"] != "confirmed" for a in result.alarms))
        self.assertIn("python_version", result.meta["environment"])

    def test_holdout_metrics_only_use_test_frames(self):
        self.cfg.set("protocol.mode", "holdout")
        self.cfg.set("protocol.dev", {"cameras":["CAM-T"],"time_ranges":[[0,90]]})
        self.cfg.set("protocol.test", {"cameras":["CAM-T"],"time_ranges":[[90,180]]})
        result = Pipeline(self.cfg, helpers.TinySource(), persist=False).run()
        self.assertIsNone(result.metrics["frame_roc_auc"])  # test interval has no positive frames
        self.assertEqual(result.metrics["camera_hours"], .025)
        self.cfg.set("protocol.test", {"cameras":["CAM-T"],"time_ranges":[[0,90]]})
        with self.assertRaises(ValueError):
            Pipeline(self.cfg, helpers.TinySource(), persist=False).run()

    def test_unavailable_authorization_never_confirms_unauthorized(self):
        candidate = Candidate("C", "CAM-01", 1, "ROI-A", "UNAUTHORIZED_INTRUSION",
                              0, 50, 50, 45, window=(0, 50))
        stage2 = Stage2Result("EVENT", (0, 50), .8, .9, .55, .25, .35,
                             validity={"mean_snr":26,"dropped_ratio":0,"occluded_ratio":0})
        verifier = RuleBasedVerifier(self.cfg, RuleEngine(RuleRegistry(self.cfg).active()),
                                    AuthorizationBook(available=False))
        self.assertEqual(verifier.verify(candidate, stage2, []).decision, "uncertain")

    def test_model_response_and_visual_input_survive_verification(self):
        candidate = Candidate("C", "CAM-01", 1, "ROI-A", "UNAUTHORIZED_INTRUSION",
                              0, 50, 50, 45, window=(0, 50))
        stage2 = Stage2Result("EVENT", (0, 50), .8, .9, .55, .25, .35,
                             validity={"mean_snr":26,"dropped_ratio":0,"occluded_ratio":0})
        response = {"card_id":"M","alarm_id":"C","camera_id":"CAM-01",
            "event_class":"UNAUTHORIZED_INTRUSION","Temporal_Anchor":{"start":0,"end":50,"keyframes":[0]},
            "Physical_Fact_Evidence":[{"fact":"reflection, not a person","frame":0,"source":"model"}],
            "Normative_Inference_Uncertainty":{"norm_ref":"","basis":"visual reflection","uncertainties":["identity unknown"]},
            "confidence":.8,"decision":"dismiss"}
        seen = []
        def transport(messages, schema):
            seen.extend(messages)
            return json.dumps(response), {"input":1,"output":1,"total":2}
        verifier = LLMVerifier(self.cfg, RuleEngine(RuleRegistry(self.cfg).active()),
            AuthorizationBook(available=True), transport=transport)
        # Provider is the video/decoder system boundary, not an internal collaborator.
        verifier.frame_provider = lambda c, s: [{"ts":0,"frame_idx":0,"url":"data:image/jpeg;base64,/9j/2Q=="}]
        result = verifier.verify(candidate, stage2, [])
        self.assertEqual(result.decision, "uncertain")  # model/rule disagreement must be explicit
        self.assertEqual(result.card["model_result"]["decision"], "dismiss")
        self.assertIn("identity unknown", result.card["Normative_Inference_Uncertainty"]["uncertainties"])
        self.assertTrue(any(f["fact"]=="reflection, not a person" for f in result.card["Physical_Fact_Evidence"]))
        self.assertTrue(any(isinstance(m["content"],list) for m in seen))
        response["Physical_Fact_Evidence"][0]["frame"] = 999
        invalid = verifier.verify(candidate, stage2, [])
        self.assertEqual(invalid.card["model_status"],"failed")
        self.assertEqual(invalid.decision,"uncertain")
        self.assertEqual(invalid.tokens["total"],2)
        verifier.transport = lambda messages,schema: ([{"invalid":"content"}], {})
        malformed = verifier.verify(candidate, stage2, [])
        self.assertEqual(malformed.decision,"uncertain")
        self.assertEqual(malformed.card["model_status"],"failed")

    def test_visual_asset_identity_changes_with_pixels_but_not_location(self):
        from cvalarm.reproducibility import calibration_context, freeze_manifest
        import shutil
        first,second = self.root/"first",self.root/"second"
        first.mkdir(); (first/"frame.jpg").write_bytes(b"image-one")
        (first/"frames.json").write_text(json.dumps({"CAM-T":[{"ts":0,"path":"frame.jpg"}]}))
        shutil.copytree(first,second)
        self.cfg.set("stage3.vlm.frames_manifest",str(first/"frames.json"))
        source = helpers.TinySource()
        ruleset = RuleRegistry(self.cfg).active()
        cal = calibrate([.01]*40,20)
        original = calibration_context(self.cfg,source)
        frozen = freeze_manifest(self.cfg,source,ruleset,cal)
        self.cfg.set("stage3.vlm.frames_manifest",str(second/"frames.json"))
        self.assertEqual(original,calibration_context(self.cfg,source))
        self.assertEqual(frozen,freeze_manifest(self.cfg,source,ruleset,cal))
        (second/"frame.jpg").write_bytes(b"image-two")
        self.assertNotEqual(original,calibration_context(self.cfg,source))

    def test_selected_model_adapters_are_reported_by_run(self):
        scores = self.root / "scores.json"
        scores.write_text(json.dumps({"CAM-T": [[0, .9], [180, .9]]}), encoding="utf-8")
        self.cfg.set("stage2.scorer.kind", "external")
        self.cfg.set("stage2.scorer.path", str(scores))
        run = Pipeline(self.cfg, helpers.TinySource(), persist=False).run()
        self.assertEqual(run.meta["models"]["localizer"]["id"], "external-series")
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            code = main(["demo", "--hours", "0.001", "--no-calibrate", "--no-report",
                         "--state-dir", str(self.root / "state"), "--out", str(self.root / "cli"),
                         "--vlm-endpoint", "http://127.0.0.1:1/not-called"])
        self.assertEqual(code, 0)
        meta = json.loads((self.root / "cli" / "models.json").read_text(encoding="utf-8"))
        self.assertEqual(meta["verifier"]["provider"], "openai-compatible")

    def test_deadline_recall_counts_missed_events(self):
        events = [GtEvent("E1", "C", "X", 0, 20, "R"),
                  GtEvent("E2", "C", "X", 100, 120, "R")]
        alarm = AlarmRecord("A", "A", "C", 1, "R", "X", 0, 1, 2, "confirmed", "EVENT")
        result = evaluate(events, [alarm], {"C": 1}, None, self.cfg.metrics)
        self.assertEqual(result["tta"]["deadline_recall"], 0.5)
        self.assertIsNone(evaluate([], [], {}, None, self.cfg.metrics)["event_recall"])
        self.assertIsNone(evaluate([], [], {}, None, self.cfg.metrics)["false_alarms_per_camera_hour"])

    def test_event_evaluation_matches_class_roi_and_unused_events(self):
        evs = [GtEvent("E1", "C", "INTRUSION", 0, 100, "R"),
               GtEvent("E2", "C", "INTRUSION", 0, 100, "R")]
        def alarm(i, cls="INTRUSION", roi="R"):
            return AlarmRecord(i, i, "C", 1, roi, cls, 0, 10, 11, "confirmed", "EVENT")
        result = evaluate(evs, [alarm("A1"), alarm("A2"), alarm("A3"),
                               alarm("A4", "DWELL"), alarm("A5", roi="OTHER")],
                          {"C": 1}, None, self.cfg.metrics)
        self.assertEqual(result["event_tp_confirmed"], 2)
        self.assertEqual(result["duplicate_alarms"], 1)
        self.assertEqual(result["false_alarms"], 2)

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.cfg = Config.load()
        self.cfg.set("runtime.state_dir", str(self.root / "state"))

    def test_cli_recovers_relocated_rule_state(self):
        registry = RuleRegistry(self.cfg)
        pointer = registry.pointer()
        pointer["path"] = "Z:/old-computer/rules.json"
        Path(registry.pointer_path).write_text(json.dumps(pointer), encoding="utf-8")
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            code = main(["demo", "--hours", "0.001", "--no-calibrate", "--no-report",
                         "--state-dir", str(self.root / "state"), "--out", str(self.root / "run")])
        self.assertEqual(code, 0)
        self.assertTrue((self.root / "run" / "run_meta.json").exists())

