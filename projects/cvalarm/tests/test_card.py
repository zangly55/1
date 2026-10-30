"""卡片结构校验与签名测试。"""
from __future__ import annotations

import copy
import unittest

import helpers  # noqa: F401

from cvalarm.card import (CARD_JSON_SCHEMA, card_to_markdown, evidence_summary, sign_card,
                          validate_card, verify_card_signature)


def card(**overrides) -> dict:
    base = {
        "card_id": "CARD-1",
        "alarm_id": "A0001",
        "camera_id": "CAM-01",
        "event_class": "UNAUTHORIZED_INTRUSION",
        "Temporal_Anchor": {"start": 10.0, "end": 20.0, "keyframes": [20, 30]},
        "Physical_Fact_Evidence": [
            {"fact": "目标锚点位于 ROI-A 内", "frame": 20, "source": "detector"},
        ],
        "Normative_Inference_Uncertainty": {
            "norm_ref": "细则 §5.2",
            "basis": "累计在场达到阈值",
            "uncertainties": [],
        },
        "confidence": 0.8,
        "decision": "confirm",
    }
    base.update(overrides)
    return base


class TestCardSchema(unittest.TestCase):
    def test_valid(self):
        self.assertEqual(validate_card(card(), ["UNAUTHORIZED_INTRUSION"]), [])

    def test_missing_field(self):
        bad = card()
        bad.pop("Temporal_Anchor")
        self.assertTrue(validate_card(bad))

    def test_event_class_not_in_enum(self):
        errors = validate_card(card(event_class="NOT_A_CLASS"), ["UNAUTHORIZED_INTRUSION"])
        self.assertTrue(any("枚举" in e for e in errors))

    def test_end_before_start(self):
        bad = card(Temporal_Anchor={"start": 20.0, "end": 10.0, "keyframes": []})
        self.assertTrue(any("不能早于" in e for e in validate_card(bad)))

    def test_empty_facts_rejected(self):
        bad = card(Physical_Fact_Evidence=[])
        self.assertTrue(any("至少" in e for e in validate_card(bad)))

    def test_fact_missing_source(self):
        bad = card(Physical_Fact_Evidence=[{"fact": "x", "frame": 1}])
        self.assertTrue(validate_card(bad))

    def test_invalid_decision(self):
        self.assertTrue(validate_card(card(decision="maybe")))

    def test_confidence_range(self):
        self.assertTrue(validate_card(card(confidence=1.5)))

    def test_schema_has_four_core_fields(self):
        props = CARD_JSON_SCHEMA["properties"]
        for field_name in ("event_class", "Temporal_Anchor", "Physical_Fact_Evidence",
                           "Normative_Inference_Uncertainty"):
            self.assertIn(field_name, props)


class TestSignature(unittest.TestCase):
    KEY = "unit-test-key"

    def test_sign_and_verify(self):
        signed = sign_card(card(), key=self.KEY)
        self.assertTrue(signed["signature"].startswith("hmac-sha256:"))
        self.assertTrue(verify_card_signature(signed, key=self.KEY))

    def test_tamper_detected(self):
        signed = sign_card(card(), key=self.KEY)
        tampered = copy.deepcopy(signed)
        tampered["confidence"] = 0.99
        self.assertFalse(verify_card_signature(tampered, key=self.KEY))

    def test_wrong_key_rejected(self):
        signed = sign_card(card(), key=self.KEY)
        self.assertFalse(verify_card_signature(signed, key="other-key"))

    def test_missing_signature(self):
        self.assertFalse(verify_card_signature(card(), key=self.KEY))


class TestHelpers(unittest.TestCase):
    def test_evidence_summary(self):
        summary = evidence_summary(card())
        self.assertEqual(summary["facts"], 1)
        self.assertEqual(summary["decision"], "confirm")

    def test_markdown_render(self):
        text = card_to_markdown(card())
        self.assertIn("画面事实", text)
        self.assertIn("规程推断", text)


if __name__ == "__main__":
    unittest.main()
