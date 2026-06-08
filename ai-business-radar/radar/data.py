"""ポートフォリオと指数構成の読込(ファイル=真実 / 原則6)。"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def load_portfolio(path: Path | None = None) -> dict:
    p = path or (ROOT / "portfolio.json")
    if not p.exists():
        raise SystemExit(f"portfolio が見つかりません: {p}")
    return json.loads(p.read_text(encoding="utf-8"))


def load_index(ref: str) -> dict:
    p = Path(ref)
    if not p.is_absolute():
        p = ROOT / p
    if not p.exists():
        raise SystemExit(f"指数構成が見つかりません: {p}")
    return json.loads(p.read_text(encoding="utf-8"))
