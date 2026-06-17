"""config.json の読込と最小検証(宣言的設定 / 原則6)。"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

REQUIRED = ["measure_currency", "policy", "benchmark"]


def load_config(path: Path | None = None) -> dict:
    p = path or (ROOT / "config.json")
    if not p.exists():
        raise SystemExit(f"config が見つかりません: {p}")
    try:
        cfg = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise SystemExit(f"config の JSON が不正: {e}")
    for k in REQUIRED:
        if k not in cfg:
            raise SystemExit(f"config に必須キーがありません: {k}")
    if not isinstance(cfg.get("policy"), dict):
        raise SystemExit("config: policy は object である必要があります")
    sat = cfg["policy"].get("satellite", {})
    if not isinstance(sat, dict):
        raise SystemExit("config: policy.satellite は object である必要があります")
    for k in ("max_pct_of_total", "max_pct_per_name", "max_pct_per_sector"):
        if isinstance(sat.get(k), bool) or not isinstance(sat.get(k), (int, float)) or sat[k] <= 0:
            raise SystemExit(f"config: policy.satellite.{k} が不正(正の数値)")
    disc = cfg["policy"].get("discipline", {})
    if not isinstance(disc, dict):
        raise SystemExit("config: policy.discipline は object であるべき")
    for k in ("chase_unrealized_pct", "averaging_down_pct", "staleness_days"):
        if k in disc and (isinstance(disc[k], bool) or not isinstance(disc[k], (int, float))):
            raise SystemExit(f"config: policy.discipline.{k} が数値でない")
    if isinstance(disc.get("staleness_days"), (int, float)) and disc["staleness_days"] < 0:
        raise SystemExit("config: policy.discipline.staleness_days は非負")
    if "value_audit" in cfg:
        _check_value_audit(cfg["value_audit"])
    return cfg


def _num(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _check_value_audit(va: dict) -> None:
    """value-audit ブロックの検証(存在時のみ。既存コマンドには影響しない)。"""
    if not isinstance(va, dict):
        raise SystemExit("config: value_audit は object である必要があります")
    if not _num(va.get("annual_hurdle_pct")) or va["annual_hurdle_pct"] <= 0:
        raise SystemExit("config: value_audit.annual_hurdle_pct は正の数値")
    if va.get("hurdle_basis") not in ("pre_tax", "post_tax"):
        raise SystemExit("config: value_audit.hurdle_basis は pre_tax|post_tax")
    if not _num(va.get("annualization_day_base")) or va["annualization_day_base"] <= 0:
        raise SystemExit("config: value_audit.annualization_day_base は正の数値")
    mn, mx = va.get("min_cycle_days"), va.get("max_cycle_days")
    if not _num(mn) or not _num(mx) or mn <= 0 or mx <= 0 or mn >= mx:
        raise SystemExit("config: value_audit.min_cycle_days < max_cycle_days(ともに正)である必要があります")
    ref = va.get("benchmark_index_ref")
    if ref is not None and not isinstance(ref, str):
        raise SystemExit("config: value_audit.benchmark_index_ref は null か文字列")
    if not _num(va.get("min_metrics_for_audit")) or va["min_metrics_for_audit"] <= 0:
        raise SystemExit("config: value_audit.min_metrics_for_audit は正の数値")
