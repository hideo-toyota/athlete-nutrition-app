"""Shared helpers for local-only research artifacts."""
from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path

from radar.features.registry import FEATURE_SET

ROOT = Path(__file__).resolve().parent.parent.parent
_ASOF_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_EDINET_RE = re.compile(r"^E\d{5}$")

FORBIDDEN_OUTPUT_TOKENS = (
    "buy_candidate",
    "recommendation",
    "expected_return",
    "期待リターン",
    "ランキング",
    "おすすめ",
    "買うべき",
    "上がる可能性が高い",
)

DISCLAIMER = (
    "これは調査用の整理であり、投資助言・売買指示・利益保証・将来予測ではありません。"
    "売買を考える場合も discipline check と人間判断が必要です。"
)


def valid_asof(asof: str | None) -> str | None:
    if asof is None:
        return None
    if not isinstance(asof, str) or not _ASOF_RE.match(asof):
        raise SystemExit(f"--asof は 'YYYY-MM-DD' で指定してください: {asof}")
    try:
        date.fromisoformat(asof)
    except ValueError as e:
        raise SystemExit(f"--asof が実在しない日付です: {asof}") from e
    return asof


def valid_edinet_code(code: str) -> str:
    if not isinstance(code, str):
        raise SystemExit("Phase D0 evidence は EDINETコード(E02367形式)のみ対応")
    code = code.strip().upper()
    if not _EDINET_RE.match(code):
        raise SystemExit("Phase D0 evidence は EDINETコード(E02367形式)のみ対応")
    return code


def feature_root(derived_root: Path | None = None) -> Path:
    return (derived_root or (ROOT / "data" / "derived")) / "features" / FEATURE_SET


def latest_asof(root: Path) -> str:
    if not root.exists():
        raise SystemExit(f"derived feature directory が見つかりません: {root}")
    dirs = sorted(p.name for p in root.iterdir() if p.is_dir() and _ASOF_RE.match(p.name))
    if not dirs:
        raise SystemExit(f"derived feature asof directory がありません: {root}")
    return dirs[-1]


def load_feature_docs(*, asof: str | None = None, derived_root: Path | None = None) -> tuple[str, list[dict]]:
    root = feature_root(derived_root)
    asof = valid_asof(asof) or latest_asof(root)
    d = root / asof
    if not d.exists():
        raise SystemExit(f"derived feature asof directory が見つかりません: {d}")
    docs = []
    for p in sorted(d.glob("*.json")):
        try:
            obj = json.loads(p.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            raise SystemExit(f"derived feature JSON が不正です({p}): {e}") from e
        if not isinstance(obj, dict):
            raise SystemExit(f"derived feature root は object である必要があります: {p}")
        if obj.get("feature_set") != FEATURE_SET:
            raise SystemExit(f"feature_set が違います: {p}")
        obj["_path"] = p
        docs.append(obj)
    if not docs:
        raise SystemExit(f"derived feature JSON がありません: {d}")
    return asof, docs


def load_feature_doc(entity: str, *, asof: str | None = None, derived_root: Path | None = None) -> tuple[str, dict]:
    code = valid_edinet_code(entity)
    root = feature_root(derived_root)
    asof = valid_asof(asof) or latest_asof(root)
    p = root / asof / f"{code}.json"
    if not p.exists():
        raise SystemExit(f"derived feature が見つかりません: {p}")
    obj = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(obj, dict):
        raise SystemExit(f"derived feature root は object である必要があります: {p}")
    obj["_path"] = p
    return asof, obj


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def metric_value(m: dict) -> str:
    if not isinstance(m, dict) or m.get("status") == "UNKNOWN":
        return "UNKNOWN"
    v = m.get("value")
    unit = m.get("unit")
    if not isinstance(v, (int, float)):
        return "UNKNOWN"
    if unit == "ratio":
        return f"{v * 100:.1f}%"
    if unit == "JPY":
        return f"{v:,.0f} JPY"
    if unit:
        return f"{v} {unit}"
    return str(v)


def assert_no_forbidden_output(text: str) -> None:
    hits = [t for t in FORBIDDEN_OUTPUT_TOKENS if t in text]
    if hits:
        raise SystemExit(f"出力禁止語が混入しています: {hits}")
