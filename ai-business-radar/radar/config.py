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
    sat = cfg["policy"].get("satellite", {})
    for k in ("max_pct_of_total", "max_pct_per_name", "max_pct_per_sector"):
        if not isinstance(sat.get(k), (int, float)) or sat[k] <= 0:
            raise SystemExit(f"config: policy.satellite.{k} が不正")
    return cfg
