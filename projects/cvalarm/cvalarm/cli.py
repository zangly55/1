"""命令行入口：初始化、跑批、标定、报告、看板、规则版本、回归门禁、反馈。"""
from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Optional, Sequence

from . import __version__
from .config import bundled_path, Config, ConfigError, load_config
from .cost import PipelineStats, compare_topologies, compute
from .feedback import AuditStore, FeedbackEntry, FeedbackStore
from .locator import calibrate, load_calibration, save_calibration
from .pipeline import Pipeline, calibrate_from_run, regression_metrics
from .probe import format_probe, probe_environment
from .report import headline, print_headline, write_report
from .rules import (RuleError, RuleRegistry, RuleSet, candidate_from_feedback,
                    regression_gate, validate_ruleset)
from .source import build_demo, build_v1, load_source, write_frames_jsonl
from .util import content_hash, get_logger, now_iso, read_json, write_json, write_jsonl

LOG = get_logger("cvalarm.cli")

BANNER = f"cvalarm {__version__} —— 持续视频监控 VLM 异常告警工程实现"


# --------------------------------------------------------------------------- 公共


def _prepare_streams() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(errors="replace")  # 兼容 GBK 控制台，绝不因中文报错
        except Exception:
            pass


def _cfg(args) -> Config:
    sets = list(getattr(args, "set", []) or [])
    files = list(getattr(args, "config", None) or [])
    profile = getattr(args, "profile", None)
    if profile:
        path = bundled_path(f"config/profiles/{profile}_scope.json")
        if not os.path.exists(path):
            raise ConfigError(f"找不到配置档案：{path}")
        files.append(path)
    cfg = load_config(files, sets=sets)
    if getattr(args, "state_dir", None):
        cfg.set("runtime.state_dir", args.state_dir)
    if getattr(args, "seed", None) is not None:
        cfg.set("runtime.seed", args.seed)
    mode = getattr(args, "verifier_mode", None)
    endpoint = getattr(args, "vlm_endpoint", None)
    model = getattr(args, "vlm_model", None)
    if mode:
        cfg.set("stage3.mode", mode)
        if endpoint:
            cfg.set("stage3.verifier", "vlm")
    if endpoint:
        cfg.set("stage3.vlm.endpoint", endpoint)
        cfg.set("stage3.verifier", "vlm")
    if model:
        cfg.set("stage3.vlm.model", model)
    return cfg


def _registry(cfg: Config) -> RuleRegistry:
    return RuleRegistry(cfg, cfg.resolve(str(cfg.get("runtime.state_dir", "state"))))


def _active_ruleset(cfg: Config, path: Optional[str] = None) -> RuleSet:
    if path:
        return RuleSet.load(cfg.resolve(path))
    return _registry(cfg).active()


def _rules_summary(ruleset: RuleSet) -> dict:
    return {
        "ruleset_id": ruleset.ruleset_id,
        "version_label": ruleset.version_label,
        "digest": ruleset.digest,
        "rules": [r.to_dict() for r in ruleset.rules],
        "policy": ruleset.policy,
    }


# --------------------------------------------------------------------------- init


def cmd_init(args) -> int:
    cfg = _cfg(args)
    root = args.dir or "."
    created = []
    for sub in ("config", "config/rules", "runs", "state"):
        path = os.path.join(root, sub)
        if not os.path.isdir(path):
            os.makedirs(path, exist_ok=True)
            created.append(path)
    registry = _registry(cfg)
    print(BANNER)
    print(f"工程根目录 : {os.path.abspath(root)}")
    print(f"当前配置   : {cfg.get('project.name')} {cfg.get('project.version')}")
    print(f"生效规则集 : {registry.active().version_label} @ {registry.active_hash}")
    print(f"关键参数   : {cfg.describe()}")
    print("新建目录   : " + (", ".join(created) if created else "（无，已存在）"))
    print("\n下一步： python run.py demo")
    return 0


# --------------------------------------------------------------------------- demo/run


def _auto_calibrate(cfg: Config, source, min_negatives: int, enabled: bool = True) -> dict:
    if not enabled:
        return {"status": "skipped"}
    # 标定需要足够多的同场景硬负例：临时提高抽样强度跑一次"标定专用"前筛，
    # 标定完成后恢复原抽样率，不影响正式运行的告警负担统计。
    old_rate = cfg.get("feedback.audit_windows_per_camera_hour")
    cfg.set("feedback.audit_windows_per_camera_hour", max(20.0, float(old_rate or 0.0)))
    try:
        probe = Pipeline(cfg, source, persist=False)
        probe.run()
    finally:
        cfg.set("feedback.audit_windows_per_camera_hour", old_rate)
    scores = [float(s.get("score", 0.0)) for s in probe.audit_samples
              if s.get("event_in_window") is False and s.get("valid_for_calibration") is True]
    cal = calibrate(scores, min_negatives=min_negatives,
                    confirm_gap=float(cfg.get("stage2.calibration.confirm_gap", 0.18)))
    save_calibration(cfg, cal)
    return cal.to_dict()


def _run_once(cfg: Config, source, out_dir: str, persist: bool = True,
              ruleset_path: Optional[str] = None, quiet: bool = False):
    ruleset = _active_ruleset(cfg, ruleset_path)
    registry = _registry(cfg)
    report = validate_ruleset(ruleset, cfg.event_classes)
    if not report.ok:
        print("规则集静态校验失败：", file=sys.stderr)
        for err in report.errors:
            print("  - " + err, file=sys.stderr)
        raise RuleError("规则集不合法，拒绝运行")
    if report.warnings and not quiet:
        for warn in report.warnings:
            LOG.debug("规则告警：%s", warn)
    pipeline = Pipeline(cfg, source, ruleset=ruleset, persist=persist, out_dir=out_dir)
    if registry.active_hash != ruleset.digest and not quiet:
        LOG.info("本次使用规则集 %s（不是当前生效版本 %s）",
                 ruleset.version_label, registry.active_hash)
    return pipeline.run()


def _print_run(result, cfg: Config, out_dir: str) -> None:
    print_headline(out_dir)
    m = result.metrics
    rel = result.reliability or {}
    proto = result.meta.get("protocol", {}) or {}
    holdout = proto.get("mode") == "holdout" and proto.get("applied")
    test_block = proto.get("test", {}) or {}
    test_cams = test_block.get("cameras") or []
    test_ranges = [(float(r[0]), float(r[1])) for r in (test_block.get("time_ranges") or [])]

    def in_test(alarm: dict) -> bool:
        if not holdout:
            return True
        if test_cams and alarm["camera_id"] not in test_cams:
            return False
        if test_ranges and not any(r0 <= alarm["t_trigger"] <= r1 for r0, r1 in test_ranges):
            return False
        return True

    print("条件召回链 : "
          f"p1={rel.get('p1_prefilter')} × p2|1={rel.get('p2_given_1_localizer')} "
          f"× p3|1,2={rel.get('p3_given_12_verifier')} → 实测 {rel.get('end_to_end_recall_observed')}")
    print("瓶颈环节   : " + str(rel.get("bottleneck")))
    if holdout:
        print(f"评测协议   : holdout — 只统计测试段（事件 {proto.get('events_in_test')}/"
              f"{proto.get('events_total')}，告警 {proto.get('alarms_in_test')}/"
              f"{proto.get('alarms_total')}）")
    print("\n告警与判定：" + ("（标 [非评测段] 的不计入指标）" if holdout else ""))
    for alarm in result.alarms:
        card = alarm.get("card") or {}
        mark = {"confirmed": "✓ 告警", "deferred": "? 转人工",
                "suppressed": "- 抑制", "system_error": "! 采集中断"}.get(alarm["status"], alarm["status"])
        tag = "" if in_test(alarm) else " [非评测段]"
        print(f"  {mark:<10} {alarm['alarm_id']:<7} {alarm['camera_id']}/{alarm['roi_id']:<6} "
              f"{alarm['event_class']:<24} t={alarm['t_trigger']:>8.1f}s "
              f"TTA={alarm['t_display'] - alarm['t_satisfy']:>5.2f}s "
              f"{('decision=' + card.get('decision', '')) if card else alarm['suppression_reason'][:24]}"
              f"{tag}")
    print("\n产物目录   : " + os.path.abspath(out_dir))


def cmd_demo(args) -> int:
    cfg = _cfg(args)
    profile = getattr(args, "profile", None) or "demo"
    if profile == "v1":
        source = build_v1(hours=float(args.hours), fps=float(args.fps))
        scope = "首版范围：单机位、两类事件"
    else:
        source = build_demo(hours=float(args.hours), fps=float(args.fps))
        scope = "完整演示：双机位、三类防区"
    out_dir = cfg.resolve(args.out or str(cfg.get("runtime.out_dir", "runs/demo")))
    print(BANNER)
    print(f"场景       : {source.name}（{args.hours}h × {len(source.cameras)} 机位 × "
          f"{args.fps}fps，{len(source.gt_events)} 个真事件）")
    print(f"范围       : {scope}")
    if not args.no_calibrate:
        print("标定       : 在非告警时段抽样硬负例，生成拒识阈值 …")
        cal = _auto_calibrate(cfg, source, int(args.min_negatives),
                             enabled=not args.no_calibrate)
        print(f"             τ_reject={cal.get('tau_reject')} τ_confirm={cal.get('tau_confirm')} "
              f"负例={cal.get('hard_negative_windows')} 版本={cal.get('version')}")
    result = _run_once(cfg, source, out_dir, ruleset_path=args.rules)
    _print_run(result, cfg, out_dir)
    if not args.no_report:
        path = write_report(out_dir, cfg)
        print("HTML 报告  : " + os.path.abspath(path))
    if args.serve:
        from .server import serve_forever

        serve_forever(out_dir, cfg, host=args.host, port=args.port)
    return 0


def cmd_run(args) -> int:
    cfg = _cfg(args)
    source = load_source(args.source, frames=cfg.resolve(args.frames or ""), cameras=cfg.resolve(args.cameras or ""),
                         gt=cfg.resolve(args.gt or ""), hours=float(args.hours), fps=float(args.fps))
    out_dir = cfg.resolve(args.out or str(cfg.get("runtime.out_dir", "runs/demo")))
    print(BANNER)
    print(f"数据源     : {args.source}")
    if args.source in ("demo", "regression") and not args.no_calibrate:
        cal = _auto_calibrate(cfg, source, int(args.min_negatives))
        print(f"标定       : τ_reject={cal.get('tau_reject')} τ_confirm={cal.get('tau_confirm')}")
    result = _run_once(cfg, source, out_dir, ruleset_path=args.rules)
    _print_run(result, cfg, out_dir)
    if not args.no_report:
        path = write_report(out_dir, cfg)
        print("HTML 报告  : " + os.path.abspath(path))
    if args.serve:
        from .server import serve_forever

        serve_forever(out_dir, cfg, host=args.host, port=args.port)
    return 0


# --------------------------------------------------------------------------- 标定/报告/看板


def cmd_calibrate(args) -> int:
    cfg = _cfg(args)
    if args.negatives_file:
        scores = [float(x) for x in json.load(open(cfg.resolve(args.negatives_file),
                                                   encoding="utf-8"))]
        cal = calibrate(scores, min_negatives=int(args.min_negatives),
                        confirm_gap=float(cfg.get("stage2.calibration.confirm_gap", 0.18)))
        save_calibration(cfg, cal)
    else:
        run_dir = cfg.resolve(args.run or str(cfg.get("runtime.out_dir", "runs/demo")))
        info = calibrate_from_run(run_dir, cfg, int(args.min_negatives))
        print(f"标定完成：{json.dumps(info, ensure_ascii=False)}")
        return 0
    print(f"标定完成：{json.dumps(cal.to_dict(), ensure_ascii=False)}")
    return 0


def cmd_report(args) -> int:
    cfg = _cfg(args)
    run_dir = cfg.resolve(args.run or str(cfg.get("runtime.out_dir", "runs/demo")))
    if not os.path.isdir(run_dir):
        print(f"运行目录不存在：{run_dir}", file=sys.stderr)
        return 2
    path = write_report(run_dir, cfg, out_path=args.out and cfg.resolve(args.out))
    print_headline(run_dir)
    print("HTML 报告  : " + os.path.abspath(path))
    return 0


def cmd_serve(args) -> int:
    from .server import serve_forever

    cfg = _cfg(args)
    run_dir = cfg.resolve(args.run or str(cfg.get("runtime.out_dir", "runs/demo")))
    if not os.path.isdir(run_dir):
        print(f"运行目录不存在：{run_dir}", file=sys.stderr)
        return 2
    print(BANNER)
    print(f"看板地址   : http://{args.host}:{args.port}/   （Ctrl+C 退出）")
    serve_forever(run_dir, cfg, host=args.host, port=args.port,
                  state_dir=cfg.resolve(args.state_dir) if args.state_dir else None)
    return 0


def cmd_probe(args) -> int:
    """接口与数据就绪度探测：模型能否加载、端点是否可用、数据是否齐全。"""
    cfg = _cfg(args)
    print(BANNER)
    state = cfg.resolve(str(cfg.get("runtime.state_dir", "state")))
    result = probe_environment(cfg, call=bool(args.call), state_dir=state)
    print(format_probe(result))
    path = os.path.join(state, "model_probe.json")
    write_json(path, result)
    print("探测记录   : " + os.path.abspath(path))
    return 0 if result["ok"] else 1


def cmd_test_report(args) -> int:
    """独立测试报告：开发/测试隔离 + 配置冻结，标定绝不在测试段上重做。"""
    cfg = _cfg(args)
    cfg.set("protocol.mode", "holdout")
    source = load_source(args.source, hours=float(args.hours), fps=float(args.fps),
                         frames=cfg.resolve(args.frames or ""), cameras=cfg.resolve(args.cameras or ""),
                         gt=cfg.resolve(args.gt or ""))
    print(BANNER)
    print("独立测试   : 配置冻结 · 标定只用开发段 · 指标只统计测试段")

    from .reproducibility import calibration_context, freeze_manifest
    cfg.validate()
    cfg.set("runtime.calibration_context", calibration_context(cfg, source))
    if not getattr(source, "ground_truth_available", True):
        raise ConfigError("独立测试需要明确的事件标注")
    check = Pipeline(cfg, source, persist=False)
    if not any(check._event_in_test(e) for e in source.gt_events):
        raise ConfigError("测试段没有可评价的正例事件；请重新划分数据，负例测试不能代表完整验收")
    freeze_path = os.path.join(cfg.resolve(str(cfg.get("runtime.state_dir", "state"))), "test_freeze.json")
    freeze = read_json(freeze_path, default=None)
    locked = bool(freeze and not args.update_freeze)
    if not locked and not args.no_dev_calibrate:
        old_rate = cfg.get("feedback.audit_windows_per_camera_hour")
        cfg.set("feedback.audit_windows_per_camera_hour", max(80.0, float(old_rate or 0.0)))
        try:
            probe = Pipeline(cfg, source, persist=False)
            probe.run()
        finally:
            cfg.set("feedback.audit_windows_per_camera_hour", old_rate)
        scores = [float(x["score"]) for x in probe.audit_samples
                  if x.get("event_in_window") is False and x.get("split") == "dev"
                  and x.get("valid_for_calibration") is True]
        save_calibration(cfg, calibrate(scores, min_negatives=int(args.min_negatives)))
    cal = load_calibration(cfg)
    if not cal.is_ok:
        raise ConfigError("标定不足或不属于本模型/场景/划分，拒绝独立测试")
    active = _active_ruleset(cfg, args.rules)
    manifest = freeze_manifest(cfg, source, active, cal)
    digest = content_hash(manifest)
    warn = ""
    if locked and freeze.get("manifest_digest") != digest:
        raise ConfigError("实际规则、标定、配置或输入与冻结清单不同；有意变更请显式 --update-freeze")
    if not locked:
        write_json(freeze_path, {"manifest_digest":digest, "config_digest":content_hash(cfg.as_dict()),
                               "manifest":manifest, "frozen_at":now_iso(),
                               "calibration":cal.to_dict(), "ruleset":active.digest})

    out_dir = cfg.resolve(args.out or "runs/test-report")
    print(f"数据源     : {args.source}（{args.hours}h × {len(source.cameras)} 机位）")
    result = _run_once(cfg, source, out_dir, ruleset_path=args.rules)
    _print_run(result, cfg, out_dir)
    proto = result.meta.get("protocol", {})
    print(f"评测协议   : mode={proto.get('mode')} 事件 {proto.get('events_in_test')}/"
          f"{proto.get('events_total')} 落在测试段，告警 {proto.get('alarms_in_test')}/"
          f"{proto.get('alarms_total')}；跳过的审计窗口 {proto.get('audit_windows_skipped', 0)}")
    payload = {
        "generated_at": now_iso(),
        "freeze": read_json(freeze_path, default={}),
        "protocol": proto,
        "headline": headline(out_dir),
        "warnings": [warn] if warn else [],
        "questions": {
            "真实事件是否保留": "见 reliability.json 的 p1/p2|1/p3|1,2 与 per_event.lost_at",
            "是否频繁打扰": "见 metrics.false_alarms_per_camera_hour 与 evaluable_video_hours",
            "证据定位是否准确": "见 metrics.localization（窗口内误差与覆盖率/精确率，与存在性分开）",
            "告警何时出现": "见 metrics.tta（阈值满足→告警）与 metrics.tta_event_start（事件起点→告警）",
            "能否在可用资源上运行": "见 resources.json（耗时/峰值内存/调用量）与 cost.json",
        },
    }
    write_json(os.path.join(out_dir, "test_report.json"), payload)
    if not args.no_report:
        path = write_report(out_dir, cfg,
                            title="独立测试报告 · 配置冻结 / 开发测试隔离")
        print("HTML 报告  : " + os.path.abspath(path))
    return 0


def cmd_metrics(args) -> int:
    cfg = _cfg(args)
    run_dir = cfg.resolve(args.run or str(cfg.get("runtime.out_dir", "runs/demo")))
    data = read_json(os.path.join(run_dir, "metrics.json"), default=None)
    if data is None:
        print(f"找不到 metrics.json：{run_dir}", file=sys.stderr)
        return 2
    keys = ["camera_hours", "events", "event_recall", "event_recall_incl_deferred",
            "precision", "false_alarms", "false_alarms_per_camera_hour", "frame_roc_auc",
            "deferred_alarms", "suppressed_alarms", "duplicate_alarms", "tta",
            "triage_counts", "no_event_rejection", "per_camera"]
    slim = {k: data.get(k) for k in keys if k in data}
    print(json.dumps(slim, ensure_ascii=False, indent=2))
    return 0


# --------------------------------------------------------------------------- 成本


def cmd_cost(args) -> int:
    cfg = _cfg(args)
    run_dir = cfg.resolve(args.run or str(cfg.get("runtime.out_dir", "runs/demo")))
    summary = read_json(os.path.join(run_dir, "run_summary.json"), default=None)
    cost = read_json(os.path.join(run_dir, "cost.json"), default=None)
    if summary is None or cost is None:
        print(f"运行产物不完整：{run_dir}", file=sys.stderr)
        return 2
    stats_dict = summary.get("stats") or {}
    stats = PipelineStats(**{k: stats_dict[k] for k in PipelineStats().__dict__
                             if k in stats_dict})
    cameras = len(read_json(os.path.join(run_dir, "run_meta.json"), default={})
                  .get("camera_hours", {})) or 1
    topologies = compare_topologies(stats, cfg.cost, cameras=cameras)
    print(BANNER)
    print(f"实测计量：机位小时={stats.camera_hours} 候选视频时={stats.candidate_video_seconds/3600:.4f}h "
          f"三级输入视频时={stats.stage3_input_seconds/3600:.4f}h")
    print(f"{'拓扑':<26}{'GPU·s/机位·h':>14}{'计算':>10}{'出站':>10}{'人工':>10}{'合计/机位·h':>14}")
    for t in topologies:
        g = t["components_gpu_seconds_per_camera_hour"]["total_gpu_seconds"]
        money = t["components_money_per_camera_hour"]
        print(f"{t['topology']:<26}{g:>14.2f}{money['compute']:>10.4f}"
              f"{money['egress']:>10.4f}{money['feedback_human']:>10.4f}{money['total']:>14.4f}")
    if args.topology:
        chosen = compute(stats, cfg.cost, topology=args.topology, cameras=cameras)
        print("\n" + json.dumps(chosen, ensure_ascii=False, indent=2))
    else:
        print("\n当前生效拓扑：" + cost.get("topology", ""))
        print(json.dumps(cost.get("components_money_per_camera_hour", {}), ensure_ascii=False))
    return 0


# --------------------------------------------------------------------------- 规则


def cmd_rules(args) -> int:
    cfg = _cfg(args)
    registry = _registry(cfg)
    action = args.rules_action
    if action == "list":
        print(f"生效规则集：{registry.active_hash} ({registry.active().version_label})")
        for item in registry.list_versions():
            mark = " *ACTIVE*" if item["active"] else ""
            print(f"  {item['hash']}  {item['version_label']:<24} {item['rule_count']:>2} 条  "
                  f"{item['created_at']}{mark}")
        return 0
    if action == "validate":
        ruleset = _active_ruleset(cfg, args.path)
        report = validate_ruleset(ruleset, cfg.event_classes)
        print(f"规则集 {ruleset.ruleset_id} @ {ruleset.version_label} (hash {ruleset.digest})")
        print(f"规则条数：{report.rule_count}　结论：{'通过' if report.ok else '不通过'}")
        for err in report.errors:
            print("  [错误] " + err)
        for warn in report.warnings:
            print("  [告警] " + warn)
        print("覆盖情况：" + json.dumps(report.coverage, ensure_ascii=False))
        return 0 if report.ok else 1
    if action == "stage":
        ruleset = RuleSet.load(cfg.resolve(args.path))
        report = validate_ruleset(ruleset, cfg.event_classes)
        if not report.ok:
            for err in report.errors:
                print("  [错误] " + err, file=sys.stderr)
            return 1
        path = registry.stage(ruleset, operator=args.operator, reason=args.reason)
        print(f"已写入隔离待审区：{path}")
        print(f"内容哈希：{ruleset.digest}")
        for warn in report.warnings:
            print("  [告警] " + warn)
        return 0
    if action == "promote":
        return _rules_promote(cfg, registry, args)
    if action == "rollback":
        try:
            info = registry.rollback(args.hash, operator=args.operator, reason=args.reason)
        except RuleError as exc:
            print(f"回滚失败：{exc}", file=sys.stderr)
            return 1
        print(f"已原子回滚到 {info['active_hash']}（{info.get('version_label', '')}），"
              f"耗时 {info['duration_ms']} ms")
        return 0
    if action == "ledger":
        for item in registry.ledger(limit=int(args.limit)):
            print(json.dumps(item, ensure_ascii=False))
        return 0
    print("未知 rules 子命令", file=sys.stderr)
    return 2


def _rules_promote(cfg: Config, registry: RuleRegistry, args) -> int:
    path = cfg.resolve(args.path) if args.path else registry.stage_path(args.hash or "")
    ruleset = RuleSet.load(path)
    report = validate_ruleset(ruleset, cfg.event_classes)
    print(f"候选规则集：{ruleset.ruleset_id} @ {ruleset.version_label} (hash {ruleset.digest})")
    for err in report.errors:
        print("  [错误] " + err, file=sys.stderr)
    for warn in report.warnings:
        print("  [告警] " + warn)
    if not report.ok:
        print("静态校验未通过，禁止发布", file=sys.stderr)
        return 1
    gate = _run_gate(cfg, ruleset, args)
    if args.dry_run:
        print("干跑模式：未发布。门禁结果：")
        print(json.dumps(gate, ensure_ascii=False, indent=2))
        return 0 if gate["passed"] else 1
    if not gate["passed"]:
        print("回归门禁未通过，禁止发布：", file=sys.stderr)
        for failure in gate["failures"]:
            print("  - " + failure, file=sys.stderr)
        return 1
    info = registry.promote(ruleset, gate, operator=args.operator, reason=args.reason)
    print(f"已原子发布：{info['active_hash']}（{ruleset.version_label}），"
          f"耗时 {info['duration_ms']} ms")
    return 0


def _run_gate(cfg: Config, candidate: RuleSet, args) -> dict:
    baseline_path = cfg.resolve(str(cfg.get("rules.gate_baseline",
                                            "state/regression_baseline.json")))
    gate_cfg = cfg.get("rules.gate", {}) or {}
    hours = float(getattr(args, "hours", 1.2) or 1.2)
    if os.path.exists(baseline_path) and not getattr(args, "update_baseline", False):
        baseline = read_json(baseline_path, default={}) or {}
    else:
        active = _registry(cfg).active()
        print("计算基线指标（使用当前生效规则集在同一回归集上重放）…")
        baseline = regression_metrics(cfg, active, hours=hours)
        write_json(baseline_path, baseline)
        print(f"基线已写入 {baseline_path}")
    print("计算候选规则集指标 …")
    candidate_metrics = regression_metrics(cfg, candidate, hours=hours)
    return regression_gate(candidate_metrics, baseline, gate_cfg)


def cmd_bench(args) -> int:
    cfg = _cfg(args)
    candidate = _active_ruleset(cfg, args.rules)
    print(BANNER)
    gate = _run_gate(cfg, candidate, args)
    print(json.dumps(gate, ensure_ascii=False, indent=2))
    return 0 if gate["passed"] else 1


# --------------------------------------------------------------------------- 反馈


def cmd_feedback(args) -> int:
    cfg = _cfg(args)
    state = cfg.resolve(str(cfg.get("runtime.state_dir", "state")))
    store = FeedbackStore(cfg, state)
    action = args.feedback_action
    if action == "add":
        entry = FeedbackEntry(
            alarm_id=args.alarm_id, verdict=args.verdict, camera_id=args.camera_id or "",
            event_class=args.event_class or "", reason_code=args.reason_code or "",
            note=args.note or "", operator=args.operator or "operator",
            ts_display=float(args.ts_display or 0.0), rule_version=args.rule_version or "",
        )
        try:
            print(json.dumps(store.add(entry), ensure_ascii=False))
        except ValueError as exc:
            print(f"反馈被拒绝：{exc}", file=sys.stderr)
            return 1
        return 0
    if action == "list":
        for item in store.entries()[-int(args.limit):]:
            print(json.dumps(item, ensure_ascii=False))
        return 0
    if action == "summary":
        print(json.dumps(store.summary(), ensure_ascii=False, indent=2))
        return 0
    if action == "audit":
        print(json.dumps(AuditStore(cfg, state).summary(), ensure_ascii=False, indent=2))
        return 0
    if action == "reflect":
        base = _active_ruleset(cfg)
        candidate = candidate_from_feedback(store.reason_counts(), base)
        report = validate_ruleset(candidate, cfg.event_classes)
        path = _registry(cfg).stage(candidate, operator=args.operator,
                                    reason="由人工驳回反馈离线反思生成")
        print(f"候选规则集已写入待审区：{path}")
        print(f"规则数：{len(candidate.rules)}　静态校验：{'通过' if report.ok else '不通过'}")
        for err in report.errors:
            print("  [错误] " + err)
        for warn in report.warnings:
            print("  [告警] " + warn)
        print("下一步： python run.py rules promote " + candidate.digest + " --dry-run")
        return 0 if report.ok else 1
    print("未知 feedback 子命令", file=sys.stderr)
    return 2


# --------------------------------------------------------------------------- 导出/自检


def cmd_export(args) -> int:
    cfg = _cfg(args)
    source = load_source(args.source, hours=float(args.hours), fps=float(args.fps))
    out = cfg.resolve(args.out)
    n = write_frames_jsonl(source, out, limit=int(args.limit or 0))
    print(f"已导出 {n} 帧检测结果到 {os.path.abspath(out)}")
    if args.cameras_out:
        path = cfg.resolve(args.cameras_out)
        write_json(path, {"cameras": [
            {**c.to_dict(), "rois": [r.to_dict() for r in source.rois
                                     if r.camera_id == c.camera_id]}
            for c in source.cameras]})
        print(f"摄像头/ROI 配置：{os.path.abspath(path)}")
    if args.gt_out:
        path = cfg.resolve(args.gt_out)
        write_jsonl(path, [e.to_dict() for e in source.gt_events])
        print(f"事件真值：{os.path.abspath(path)}")
    return 0


def cmd_selftest(args) -> int:
    import unittest

    cfg = _cfg(args)
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    tests_dir = os.path.join(root, "tests")
    print(BANNER)
    print(f"配置校验   : 通过（{cfg.get('project.name')} {cfg.get('project.version')}）")
    print(f"标定状态   : {json.dumps(load_calibration(cfg).to_dict(), ensure_ascii=False)}")
    loader = unittest.TestLoader()
    suite = loader.discover(tests_dir)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return 0 if result.wasSuccessful() else 1


# --------------------------------------------------------------------------- 参数


def build_parser() -> argparse.ArgumentParser:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--config", action="append", default=[],
                        help="追加覆盖配置文件（可重复），如 config/site.json")
    common.add_argument("--set", action="append", default=[],
                        help="点号路径覆盖，如 --set fsm.dwell_threshold_s=60")
    common.add_argument("--state-dir", default=None, help="状态目录（规则/反馈/标定）")
    common.add_argument("--seed", type=int, default=None, help="随机种子")
    common.add_argument("--log-level", default=None, help="debug/info/warning")

    p = argparse.ArgumentParser(prog="cvalarm", description=BANNER, parents=[common])
    p.add_argument("--version", action="version", version=f"cvalarm {__version__}")
    sub = p.add_subparsers(dest="command", required=True)

    s = sub.add_parser("init", help="检查并初始化工程目录与规则版本仓库", parents=[common])
    s.add_argument("--dir", default=None)
    s.set_defaults(func=cmd_init)

    run_opts = argparse.ArgumentParser(add_help=False)
    run_opts.add_argument("--out", default=None, help="运行产物目录")
    run_opts.add_argument("--profile", default=None, choices=["v1"],
                          help="配置档案：v1 = 首版范围（单机位、两类事件）")
    run_opts.add_argument("--hours", type=float, default=3.0, help="合成场景时长（小时）")
    run_opts.add_argument("--fps", type=float, default=2.0, help="抽帧帧率")
    run_opts.add_argument("--rules", default=None, help="指定规则集文件（默认用生效版本）")
    run_opts.add_argument("--no-report", action="store_true", help="不生成 HTML 报告")
    run_opts.add_argument("--no-calibrate", action="store_true", help="跳过自动标定")
    run_opts.add_argument("--min-negatives", type=int, default=20, help="标定所需硬负例数")
    run_opts.add_argument("--verifier-mode", default=None,
                          choices=["baseline", "cot_selfcheck", "role_pipeline",
                                   "adversarial_falsifier"],
                          help="Stage3 交互架构（需配合 --vlm-endpoint 生效）")
    run_opts.add_argument("--vlm-endpoint", default=None, help="OpenAI 兼容 /chat/completions 端点")
    run_opts.add_argument("--vlm-model", default=None, help="模型名")
    run_opts.add_argument("--serve", action="store_true", help="运行后启动看板")
    run_opts.add_argument("--host", default="127.0.0.1")
    run_opts.add_argument("--port", type=int, default=8080)

    s = sub.add_parser("demo", help="一键跑演示场景（含自动标定与报告）", parents=[common, run_opts])
    s.set_defaults(func=cmd_demo)

    s = sub.add_parser("run", help="在指定数据源上跑批", parents=[common, run_opts])
    s.add_argument("--source", default="demo", choices=["demo", "v1", "regression", "jsonl"])
    s.add_argument("--frames", default=None, help="jsonl 数据源：逐帧检测文件")
    s.add_argument("--cameras", default=None, help="jsonl 数据源：摄像头/ROI 配置")
    s.add_argument("--gt", default=None, help="jsonl 数据源：事件真值")
    s.set_defaults(func=cmd_run)

    s = sub.add_parser("probe", help="模型与接口就绪度探测（可做一次真实调用）", parents=[common])
    s.add_argument("--call", action="store_true", help="对已配置的 VLM 端点做一次真实调用")
    s.set_defaults(func=cmd_probe)

    s = sub.add_parser("test-report",
                       help="独立测试报告（配置冻结 + 开发/测试隔离）",
                       parents=[common, run_opts])
    s.add_argument("--source", default="demo", choices=["demo", "v1", "regression", "jsonl"])
    s.add_argument("--frames", help="jsonl 检测文件")
    s.add_argument("--cameras", help="相机及 ROI 配置")
    s.add_argument("--gt", help="事件真值文件（独立测试必需）")
    s.add_argument("--update-freeze", action="store_true", help="重新冻结当前配置")
    s.add_argument("--no-dev-calibrate", action="store_true",
                   help="跳过开发段标定，直接用已有标定产物")
    s.set_defaults(func=cmd_test_report)

    s = sub.add_parser("calibrate", help="用硬负例分数标定拒识阈值", parents=[common])
    s.add_argument("--run", default=None)
    s.add_argument("--negatives-file", default=None, help="硬负例分数 JSON 数组")
    s.add_argument("--min-negatives", type=int, default=20)
    s.set_defaults(func=cmd_calibrate)

    s = sub.add_parser("report", help="重新生成 HTML 报告", parents=[common])
    s.add_argument("--run", default=None)
    s.add_argument("--out", default=None)
    s.set_defaults(func=cmd_report)

    s = sub.add_parser("serve", help="启动实时看板", parents=[common])
    s.add_argument("--run", default=None)
    s.add_argument("--host", default="127.0.0.1")
    s.add_argument("--port", type=int, default=8080)
    s.set_defaults(func=cmd_serve)

    s = sub.add_parser("metrics", help="打印评测指标摘要", parents=[common])
    s.add_argument("--run", default=None)
    s.set_defaults(func=cmd_metrics)

    s = sub.add_parser("cost", help="打印成本核算与拓扑对比", parents=[common])
    s.add_argument("--run", default=None)
    s.add_argument("--topology", default=None,
                   choices=["edge-only", "edge-gateway-cascade", "edge-cloud-api"])
    s.set_defaults(func=cmd_cost)

    s = sub.add_parser("rules", help="规则集：校验/暂存/发布/回滚/账本", parents=[common])
    rsub = s.add_subparsers(dest="rules_action", required=True)
    r = rsub.add_parser("list", parents=[common])
    r.set_defaults(func=cmd_rules)
    r = rsub.add_parser("validate", parents=[common])
    r.add_argument("--path", default=None)
    r.set_defaults(func=cmd_rules)
    r = rsub.add_parser("stage", parents=[common])
    r.add_argument("path")
    r.add_argument("--operator", default="operator")
    r.add_argument("--reason", default="")
    r.set_defaults(func=cmd_rules)
    r = rsub.add_parser("promote", parents=[common])
    r.add_argument("path", nargs="?", default=None, help="候选规则集文件；缺省用 --hash 指待审区")
    r.add_argument("--hash", default=None, help="待审区哈希前缀")
    r.add_argument("--operator", default="operator")
    r.add_argument("--reason", default="")
    r.add_argument("--dry-run", action="store_true")
    r.add_argument("--update-baseline", action="store_true")
    r.add_argument("--hours", type=float, default=1.2)
    r.set_defaults(func=cmd_rules)
    r = rsub.add_parser("rollback", parents=[common])
    r.add_argument("hash")
    r.add_argument("--operator", default="operator")
    r.add_argument("--reason", default="回滚到稳定版本")
    r.set_defaults(func=cmd_rules)
    r = rsub.add_parser("ledger", parents=[common])
    r.add_argument("--limit", type=int, default=30)
    r.set_defaults(func=cmd_rules)

    s = sub.add_parser("bench", help="回归门禁：候选规则集 vs 基线", parents=[common])
    s.add_argument("--rules", default=None, help="候选规则集文件")
    s.add_argument("--hours", type=float, default=1.2)
    s.add_argument("--update-baseline", action="store_true")
    s.add_argument("--operator", default="operator")
    s.add_argument("--reason", default="")
    s.set_defaults(func=cmd_bench)

    s = sub.add_parser("feedback", help="人工反馈：录入/列表/汇总/反思", parents=[common])
    fsub = s.add_subparsers(dest="feedback_action", required=True)
    f = fsub.add_parser("add", parents=[common])
    f.add_argument("--alarm-id", required=True)
    f.add_argument("--verdict", required=True, choices=["confirm", "dismiss", "uncertain"])
    f.add_argument("--reason-code", default=None)
    f.add_argument("--note", default="")
    f.add_argument("--operator", default="operator")
    f.add_argument("--camera-id", default=None)
    f.add_argument("--event-class", default=None)
    f.add_argument("--rule-version", default=None)
    f.add_argument("--ts-display", type=float, default=0.0)
    f.set_defaults(func=cmd_feedback)
    f = fsub.add_parser("list", parents=[common])
    f.add_argument("--limit", type=int, default=20)
    f.set_defaults(func=cmd_feedback)
    f = fsub.add_parser("summary", parents=[common])
    f.set_defaults(func=cmd_feedback)
    f = fsub.add_parser("audit", parents=[common])
    f.set_defaults(func=cmd_feedback)
    f = fsub.add_parser("reflect", parents=[common])
    f.add_argument("--operator", default="operator")
    f.set_defaults(func=cmd_feedback)

    s = sub.add_parser("export-frames", help="导出逐帧检测 JSONL（用于复现/接真实系统）",
                       parents=[common])
    s.add_argument("--source", default="demo", choices=["demo", "regression"])
    s.add_argument("--out", default="data/frames_demo.jsonl")
    s.add_argument("--cameras-out", default="data/cameras_demo.json")
    s.add_argument("--gt-out", default="data/gt_demo.jsonl")
    s.add_argument("--limit", type=int, default=0)
    s.add_argument("--hours", type=float, default=3.0)
    s.add_argument("--fps", type=float, default=2.0)
    s.set_defaults(func=cmd_export)

    s = sub.add_parser("selftest", help="配置自检 + 运行单元测试", parents=[common])
    s.set_defaults(func=cmd_selftest)

    return p


def main(argv: Optional[Sequence[str]] = None) -> int:
    _prepare_streams()
    parser = build_parser()
    args = parser.parse_args(argv)
    if getattr(args, "log_level", None):
        LOG.setLevel(args.log_level.upper())
        get_logger().setLevel(args.log_level.upper())
    try:
        return int(args.func(args) or 0)
    except ConfigError as exc:
        print(f"配置错误：{exc}", file=sys.stderr)
        return 2
    except RuleError as exc:
        print(f"规则错误：{exc}", file=sys.stderr)
        return 2
    except ValueError as exc:
        print(f"参数错误：{exc}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("\n已中断", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
