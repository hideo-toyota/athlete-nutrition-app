"""ポートフォリオと指数構成の読込(ファイル=真実 / 原則6)。"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _read_json(p: Path, what: str) -> dict:
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise SystemExit(f"{what} の JSON が不正です({p}): {e}")
    if not isinstance(data, dict):
        raise SystemExit(f"{what} は object である必要があります: {p}")
    return data


def load_portfolio(path: Path | None = None) -> dict:
    p = path or (ROOT / "portfolio.json")
    if not p.exists():
        raise SystemExit(f"portfolio が見つかりません: {p}")
    return _read_json(p, "portfolio")


def load_index(ref: str) -> dict:
    if not isinstance(ref, str) or not ref.strip():
        raise SystemExit("指数構成 ref が空です")
    base = (ROOT / "indices").resolve()
    p = Path(ref)
    if p.is_absolute():
        p = p.resolve()
    else:
        text = ref.replace("\\", "/")
        if text.startswith("indices/"):
            text = text[len("indices/"):]
        p = (base / text).resolve()
    try:
        p.relative_to(base)
    except ValueError:
        raise SystemExit(f"指数構成 ref は indices/ 配下のみ許可: {ref!r}")
    if not p.exists():
        raise SystemExit(f"指数構成が見つかりません: {p}")
    return _read_json(p, "指数構成")
