"""Content identities independent of the checkout's absolute path."""
import copy
import hashlib
import os
import json
from pathlib import Path
from .util import content_hash


def environment_info():
    import platform
    from importlib.metadata import version, PackageNotFoundError
    packages = {}
    for name in ("opencv-python", "ultralytics", "torch"):
        try:
            packages[name] = version(name)
        except PackageNotFoundError:
            packages[name] = None
    return {"python_version":platform.python_version(), "implementation":platform.python_implementation(),
            "system":platform.system(), "machine":platform.machine(), "optional_packages":packages}


def input_files(cfg, source):
    files = {key:file_digest(getattr(source,key,None))
             for key in ("frames_path","cameras_path","gt_path","video_path")}
    for key in ("stage2.scorer.path","stage3.authorization_file"):
        value = cfg.get(key)
        files[key] = file_digest(cfg.resolve(value)) if value else None
    manifest = cfg.get("stage3.vlm.frames_manifest")
    if manifest:
        path = Path(cfg.resolve(manifest))
        try:
            rows = json.loads(path.read_text(encoding="utf-8"))
            assets = {camera:[{**{k:v for k,v in row.items() if k != "path"},
                                "image_sha256":file_digest(path.parent / row["path"])} for row in frames]
                      for camera,frames in rows.items()}
            files["stage3.vlm.frames_manifest"] = content_hash(assets)
        except (OSError, ValueError, TypeError, KeyError, AttributeError):
            files["stage3.vlm.frames_manifest"] = {"invalid_manifest_sha256":file_digest(path)}
    from .evidence import media_info
    files["media"] = {camera:file_digest(media_info(cfg,camera).get("path"))
                      for camera in cfg.get("deployment.media.cameras",{})}
    return files


def file_digest(path):
    if not path or not os.path.isfile(path):
        return None
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def calibration_context(cfg, source):
    scorer = copy.deepcopy(cfg.get("stage2.scorer", {}))
    if scorer.get("path"):
        scorer["path"] = file_digest(cfg.resolve(scorer["path"]))
    identity = {
        "source": source.describe(),
        "files": input_files(cfg, source),
        "rois": [r.to_dict() for r in source.rois],
        "scorer": scorer, "weights": cfg.get("stage2.weights"),
        "bin_seconds": cfg.get("stage2.bin_seconds"),
        "validity": cfg.get("stage2.validity"),
        "models": cfg.get("models"), "protocol": cfg.get("protocol"),
    }
    return content_hash(identity)


def freeze_manifest(cfg, source, ruleset, calibration):
    data = cfg.as_dict()
    runtime = data.get("runtime", {})
    for key in ("state_dir", "out_dir"):
        runtime.pop(key, None)
    # Artifact locations do not change the experiment; evidence content does.
    files = input_files(cfg,source)
    data.get("stage2",{}).get("calibration",{}).pop("artifact",None)
    if data.get("stage2",{}).get("scorer",{}).get("path"):
        data["stage2"]["scorer"]["path"] = files["stage2.scorer.path"]
    if data.get("stage3",{}).get("authorization_file"):
        data["stage3"]["authorization_file"] = files["stage3.authorization_file"]
    if data.get("stage3",{}).get("vlm",{}).get("frames_manifest"):
        data["stage3"]["vlm"]["frames_manifest"] = files["stage3.vlm.frames_manifest"]
    if "media" in data.get("deployment",{}):
        data["deployment"]["media"] = {"content":files["media"]}
    rules = data.get("rules",{})
    for key in ("active","ledger","versions_dir","staged_dir","active_pointer"):
        rules.pop(key,None)
    for key in ("path","audit_path"):
        data.get("feedback",{}).pop(key,None)
    cal = calibration.to_dict()
    cal.pop("created_at", None)
    return {"config":data, "calibration":cal, "ruleset":ruleset.digest,
            "source_context":calibration_context(cfg, source)}
