"""Operational diagnostics for ai-business-radar.

`radar doctor` is intentionally local-only: it does not read provider raw
bodies, does not call network APIs, and never prints secret values.
"""
from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from .runtime_guard import canonical_status


KNOWN_SECRET_KEYS = (
    "JQUANTS_API_KEY",
    "EDINETDB_API_KEY",
    "JQUANTS_REFRESH_TOKEN",
    "JQUANTS_MAILADDRESS",
    "JQUANTS_PASSWORD",
)


@dataclass(frozen=True)
class LatestDir:
    asof: str | None
    path: str | None
    count: int | None


def _is_asof_dir(path: Path) -> bool:
    name = path.name
    if len(name) != 10 or name[4] != "-" or name[7] != "-":
        return False
    try:
        datetime.strptime(name, "%Y-%m-%d")
    except ValueError:
        return False
    return True


def _latest_dir(base: Path, *, root: Path, pattern: str = "*", exclude_suffixes: tuple[str, ...] = ()) -> LatestDir:
    if not base.exists():
        return LatestDir(None, None, None)
    dirs = sorted(p for p in base.iterdir() if p.is_dir() and _is_asof_dir(p))
    if not dirs:
        return LatestDir(None, None, None)
    latest = dirs[-1]
    files = [
        p for p in latest.glob(pattern)
        if p.is_file() and not any(p.name.endswith(suffix) for suffix in exclude_suffixes)
    ]
    return LatestDir(latest.name, _rel(latest, root), len(files))


def _rel(path: Path | None, root: Path) -> str | None:
    if path is None:
        return None
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def _safe_json(path: Path) -> dict | None:
    if not path.exists():
        return None
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return obj if isinstance(obj, dict) else None


def _runtime_status(root: Path) -> dict:
    cfg = _safe_json(root / "config.json") or {}
    status = canonical_status(root, cfg)
    return status


def _latest_matching_file(base: Path, pattern: str) -> Path | None:
    if not base.exists():
        return None
    files = sorted(p for p in base.glob(pattern) if p.is_file())
    return files[-1] if files else None


def _line_count(path: Path) -> int:
    if not path.exists():
        return 0
    try:
        return sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip())
    except OSError:
        return 0


def _env_status(root: Path) -> dict:
    path = root / ".env"
    status = {
        "exists": path.exists(),
        "known": {k: "MISSING" for k in KNOWN_SECRET_KEYS},
        "extra_line_count": 0,
        "malformed_line_count": 0,
    }
    if not path.exists():
        return status
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        status["readable"] = False
        return status
    status["readable"] = True
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if "=" not in stripped:
            status["malformed_line_count"] += 1
            continue
        key, value = stripped.split("=", 1)
        key = key.strip()
        if key in status["known"]:
            status["known"][key] = "SET" if value.strip() else "EMPTY"
        else:
            status["extra_line_count"] += 1
    return status


def _git_info(root: Path) -> dict:
    def run(args: list[str]) -> str | None:
        try:
            proc = subprocess.run(
                ["git", *args],
                cwd=root,
                text=True,
                capture_output=True,
                timeout=5,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            return None
        if proc.returncode != 0:
            return None
        return proc.stdout.strip()

    status = run(["status", "--short"])
    return {
        "branch": run(["branch", "--show-current"]) or "UNKNOWN",
        "commit": run(["rev-parse", "--short", "HEAD"]) or "UNKNOWN",
        "dirty": bool(status),
        "status_count": len(status.splitlines()) if status else 0,
    }


def _journal_status(root: Path) -> dict:
    path = root / "decision_log.jsonl"
    if not path.exists():
        return {"path": "decision_log.jsonl", "exists": False, "decisions": 0, "outcomes": 0, "bad_lines": 0}
    decisions = 0
    outcomes = 0
    bad = 0
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            bad += 1
            continue
        if not isinstance(obj, dict):
            bad += 1
            continue
        if obj.get("type") == "outcome":
            outcomes += 1
        else:
            decisions += 1
    return {"path": "decision_log.jsonl", "exists": True, "decisions": decisions, "outcomes": outcomes, "bad_lines": bad}


def _feature_latest(root: Path, feature_set: str, pattern: str) -> LatestDir:
    return _latest_dir(root / "data" / "derived" / "features" / feature_set, root=root, pattern=pattern)


def _raw_latest(root: Path, provider: str, dataset: str) -> LatestDir:
    return _latest_dir(
        root / "data" / "raw" / provider / dataset,
        root=root,
        pattern="*.json",
        exclude_suffixes=(".meta.json", ".provenance.json"),
    )


def _jquants_status(root: Path) -> dict:
    manifest_path = _latest_matching_file(root / "data" / "derived" / "features" / "jquants_equity_v1", "*/manifest.json")
    manifest = _safe_json(manifest_path) if manifest_path else None
    coverage = (manifest or {}).get("coverage") if isinstance(manifest, dict) else {}
    bulk_manifest_path = _latest_matching_file(root / "data" / "metadata", "jquants_bulk_download_*.json")
    bulk_manifest = _safe_json(bulk_manifest_path) if bulk_manifest_path else None
    return {
        "derived": _feature_latest(root, "jquants_equity_v1", "features.jsonl"),
        "features_rows": _line_count((manifest_path.parent / "features.jsonl") if manifest_path else Path()),
        "latest_price_date": coverage.get("latest_price_date") if isinstance(coverage, dict) else None,
        "price_coverage_ratio": coverage.get("price_coverage_ratio") if isinstance(coverage, dict) else None,
        "valuation_coverage_ratio": coverage.get("valuation_coverage_ratio") if isinstance(coverage, dict) else None,
        "bulk_manifest": _rel(bulk_manifest_path, root) if bulk_manifest_path else None,
        "bulk_files": (bulk_manifest or {}).get("downloaded_files") or (bulk_manifest or {}).get("total_files"),
    }


def _audit_status(root: Path) -> dict:
    path = root / "outputs" / "data_quality_audit.json"
    obj = _safe_json(path)
    if obj is None:
        return {"exists": False}
    cross = obj.get("cross_check") if isinstance(obj.get("cross_check"), dict) else {}
    val = obj.get("valuation") if isinstance(obj.get("valuation"), dict) else {}
    metrics = cross.get("metrics") if isinstance(cross.get("metrics"), dict) else {}
    top = []
    for name, metric in metrics.items():
        if not isinstance(metric, dict):
            continue
        rate = metric.get("mismatch_rate")
        if isinstance(rate, (int, float)):
            top.append((rate, name, metric.get("calibration_signal")))
    top.sort(reverse=True)
    return {
        "exists": True,
        "asof": obj.get("asof"),
        "cross_checked_items": cross.get("cross_checked_items"),
        "valuation_coverage_ratio": val.get("valuation_coverage_ratio"),
        "top_mismatch": top[:3],
    }


def build_doctor_report(root: Path) -> dict:
    root = root.resolve()
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "root": str(root),
        "root_under_private_tmp": str(root).startswith("/private/tmp/"),
        "runtime": _runtime_status(root),
        "git": _git_info(root),
        "env": _env_status(root),
        "journal": _journal_status(root),
        "data": {
            "raw_companies": _raw_latest(root, "edinet-db", "companies"),
            "raw_financials": _raw_latest(root, "edinet-db", "financials"),
            "derived_company_map": _feature_latest(root, "edinet_company_map_v1", "companies.jsonl"),
            "derived_edinet_financials": _feature_latest(root, "edinet_financials_v1", "E*.json"),
            "jquants": _jquants_status(root),
        },
        "audit": _audit_status(root),
        "outputs": {
            "latest_discord_prompt": _rel(_latest_matching_file(root / "outputs" / "discord", "llm_prompt_*.md"), root),
            "latest_llm_handoff": _rel(_latest_matching_file(root / "outputs" / "llm_handoff", "*.md"), root),
        },
    }
    report["warnings"] = _warnings(report)
    return report


def _warnings(report: dict) -> list[str]:
    warnings: list[str] = []
    if report.get("root_under_private_tmp"):
        warnings.append("repo_under_private_tmp: 正本パスとしては消失/混乱リスクがあります")
    runtime = report.get("runtime") or {}
    if runtime.get("configured") and runtime.get("is_canonical") is False:
        warnings.append(
            "canonical_root_mismatch: このcheckoutは正本ではありません"
            f" current={runtime.get('current_root')} expected={runtime.get('canonical_root')}"
        )
    if report["git"].get("dirty"):
        warnings.append(f"git_dirty: 未コミット/未追跡の差分 {report['git'].get('status_count')} 件")
    journal = report["journal"]
    if not journal.get("exists") or journal.get("decisions", 0) == 0:
        warnings.append("decision_log_empty: 検証ループの燃料がまだ入っていません")
    if journal.get("bad_lines"):
        warnings.append("decision_log_bad_lines: 壊れた JSONL 行があります")

    data = report["data"]
    raw_fin = data["raw_financials"].asof
    derived_fin = data["derived_edinet_financials"].asof
    if raw_fin and (not derived_fin or derived_fin < raw_fin):
        warnings.append(f"edinet_features_stale: raw financials {raw_fin} > derived {derived_fin or 'NONE'}")
    raw_companies = data["raw_companies"].asof
    company_map = data["derived_company_map"].asof
    if raw_companies and (not company_map or company_map < raw_companies):
        warnings.append(f"company_map_stale: raw companies {raw_companies} > derived map {company_map or 'NONE'}")
    jq = data["jquants"]
    if not jq["derived"].asof:
        warnings.append("jquants_features_missing: J-Quants derived がありません")
    return warnings


def _fmt_pct(value) -> str:
    return f"{value * 100:.1f}%" if isinstance(value, (int, float)) else "UNKNOWN"


def _fmt_latest(name: str, latest: LatestDir) -> str:
    if latest.asof is None:
        return f"- {name}: NONE"
    count = latest.count if latest.count is not None else "UNKNOWN"
    return f"- {name}: asof={latest.asof} files={count} path={latest.path}"


def render_doctor_report(report: dict) -> str:
    env = report["env"]
    data = report["data"]
    jq = data["jquants"]
    audit = report["audit"]
    lines = [
        "# ai-business-radar doctor",
        "",
        "これはローカル診断です。APIキー値・.env値・provider raw本文は表示しません。",
        "",
        "## Workspace",
        f"- root: {report['root']}",
        f"- canonical_root: {report['runtime'].get('canonical_root') or 'UNCONFIGURED'}",
        f"- canonical_match: {report['runtime'].get('is_canonical') if report['runtime'].get('configured') else 'UNKNOWN'}",
        f"- git: branch={report['git']['branch']} commit={report['git']['commit']} dirty={report['git']['dirty']}",
        f"- private_tmp: {report['root_under_private_tmp']}",
        "",
        "## Secrets Presence",
        f"- .env: {'present' if env.get('exists') else 'missing'}",
    ]
    for key in KNOWN_SECRET_KEYS:
        lines.append(f"- {key}: {env['known'].get(key, 'MISSING')}")
    lines.extend([
        f"- extra_env_lines: {env.get('extra_line_count', 0)}",
        f"- malformed_env_lines: {env.get('malformed_line_count', 0)}",
        "",
        "## Data Freshness",
        _fmt_latest("raw edinet companies", data["raw_companies"]),
        _fmt_latest("raw edinet financials", data["raw_financials"]),
        _fmt_latest("derived company map", data["derived_company_map"]),
        _fmt_latest("derived edinet financials", data["derived_edinet_financials"]),
        _fmt_latest("derived jquants equity", jq["derived"]),
        f"- J-Quants features rows: {jq['features_rows']}",
        f"- J-Quants latest price date: {jq['latest_price_date'] or 'UNKNOWN'}",
        f"- J-Quants price coverage: {_fmt_pct(jq['price_coverage_ratio'])}",
        f"- J-Quants valuation coverage: {_fmt_pct(jq['valuation_coverage_ratio'])}",
        f"- latest J-Quants bulk manifest: {jq['bulk_manifest'] or 'NONE'}",
        "",
        "## Verification Loop",
        f"- decision_log exists: {report['journal']['exists']}",
        f"- decisions: {report['journal']['decisions']} / outcomes: {report['journal']['outcomes']} / bad_lines: {report['journal']['bad_lines']}",
        "",
        "## Data Quality Audit",
    ])
    if audit.get("exists"):
        lines.extend([
            f"- asof: {audit.get('asof')}",
            f"- cross_checked_items: {audit.get('cross_checked_items')}",
            f"- valuation_coverage: {_fmt_pct(audit.get('valuation_coverage_ratio'))}",
        ])
        if audit.get("top_mismatch"):
            lines.append("- top mismatch:")
            for rate, name, signal in audit["top_mismatch"]:
                lines.append(f"  - {name}: {_fmt_pct(rate)} signal={signal or 'UNKNOWN'}")
    else:
        lines.append("- NONE")
    lines.extend([
        "",
        "## Latest Outputs",
        f"- discord prompt: {report['outputs']['latest_discord_prompt'] or 'NONE'}",
        f"- llm handoff: {report['outputs']['latest_llm_handoff'] or 'NONE'}",
        "",
        "## Warnings",
    ])
    if report["warnings"]:
        lines.extend(f"- {w}" for w in report["warnings"])
    else:
        lines.append("- none")
    lines.append("")
    return "\n".join(lines)


def write_doctor_report(report: dict, *, root: Path) -> Path:
    out = root / "outputs" / "doctor.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render_doctor_report(report), encoding="utf-8")
    return out
