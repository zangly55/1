# Approved optimization scope

User approved local implementation, TDD and review on 2026-10-30; no Kimi and no real model resources are currently available.

Deliver a portable project with reliable matching/holdout/calibration, meaningful model adapters, preserved model conclusions, honest latency/resource reporting, reproducible runs and usable review actions.

Work through complete behaviors: portable CLI; accurate evaluation; explicit model configuration/visual inputs/results; reproducible calibration and snapshots; dashboard feedback.

Acceptance boundaries: CLI invocations, pipeline outputs with known input/labels, externally injected model transports, and dashboard HTTP APIs. Keep each red/green slice small; use existing unittest conventions. Real model quality/GPU benchmarks require future user resources and must remain marked untested.

No automatic model downloads, paid services, external publishing, new Codex chats or Kimi delegation.

Status: implemented and verified; see docs/验证记录.md. Real-model validation remains explicitly outside this delivery.

