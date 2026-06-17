"""value-audit の入力検証 + 追記専用 JSONL I/O + 安全(ticker/path)。

EARNINGS_CYCLE_VALUE_AUDIT_SPEC / PLAN 準拠:
- ticker 厳格検証 + safe slug + path traversal 禁止(§2.5)。
- value_thesis / cycle_outcome は **追記専用 JSONL**(原本不変・amends/supersedes)。
- active_theses(): amends/supersedes を一意に解決(§2.1)。不正参照・循環・複数有効版は停止。
- append_outcome(): 冪等キーで重複採点を拒否(§2.2)。
- **買い意思フィールド禁止 / 必須項目 / anti_thesis 品質ゲート**(§2.1・§3)。
"""
from __future__ import annotations

import json
import re
import uuid
from datetime import date, datetime
from pathlib import Path

from . import value_audit as va

ROOT = Path(__file__).resolve().parent.parent
JOURNAL = ROOT / "journal"
THESIS_LOG = JOURNAL / "value_thesis.jsonl"
OUTCOME_LOG = JOURNAL / "value_outcomes.jsonl"
OUTPUTS = ROOT / "outputs"
VALUE_AUDIT_OUT = OUTPUTS / "value_audit"

SCHEMA_VERSION = "2"

_TICKER_RE = re.compile(r"^[A-Za-z0-9._-]{1,15}$")
_RESERVED_SLUGS = {"", ".", ".."}

# 買い意思・優劣・推奨に見えるフィールドは持たせない(§2.1)
FORBIDDEN_FIELDS = {
    "buy_intent", "entry_plan", "target_price", "position_size",
    "rank", "score", "recommendation", "buy_candidate",
}
VALID_POSITION_INTENT = {"paper_only", "existing_holding_review"}
VALID_CHEAPNESS_CLASS = {
    "temporary_setback", "structural_decay", "mispricing_hypothesis", "unknown",
}
# anti_thesis が形骸化(コピペ/プレースホルダ)していないかの最低限ゲート
_PLACEHOLDERS = {"", "...", "…", "todo", "tbd", "n/a", "na", "なし", "未記入", "ー", "-"}
_MIN_TEXT_LEN = 8


# ---------------------------------------------------------------------------
# 日付 / PIT
# ---------------------------------------------------------------------------
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def valid_asof(asof: str | None) -> date | None:
    if asof is None:
        return None
    if not _DATE_RE.match(asof):
        raise SystemExit(f"--asof は 'YYYY-MM-DD' で指定してください: {asof}")
    try:
        return date.fromisoformat(asof)
    except ValueError:
        raise SystemExit(f"--asof が実在しない日付です: {asof}")


def parse_dt_date(s: str, what: str) -> date:
    """ISO8601(date または datetime, tz 付き可)から date 部分を取り出す。"""
    if not isinstance(s, str) or not s.strip():
        raise SystemExit(f"{what} は ISO8601 文字列で必須です: {s!r}")
    txt = s.strip()
    try:
        if "T" in txt or " " in txt:
            return datetime.fromisoformat(txt.replace("Z", "+00:00")).date()
        return date.fromisoformat(txt)
    except ValueError:
        raise SystemExit(f"{what} が ISO8601 として不正です: {s!r}")


# ---------------------------------------------------------------------------
# ticker / path safety(§2.5)
# ---------------------------------------------------------------------------
def validate_ticker(s) -> str:
    """ticker を厳格検証し safe slug を返す。traversal・予約名・全角・空は拒否。"""
    if not isinstance(s, str) or not _TICKER_RE.match(s):
        raise SystemExit(f"ticker は {_TICKER_RE.pattern} に一致する必要があります: {s!r}")
    slug = s
    if slug in _RESERVED_SLUGS:
        raise SystemExit(f"ticker が予約名のため使用できません: {s!r}")
    return slug


def safe_output_path(slug: str) -> Path:
    """outputs/value_audit/<slug>.md を返す。resolved path が当該ディレクトリ外なら停止。"""
    if slug in _RESERVED_SLUGS:
        raise SystemExit(f"slug が不正です: {slug!r}")
    base = VALUE_AUDIT_OUT.resolve()
    p = (VALUE_AUDIT_OUT / f"{slug}.md").resolve()
    if p.parent != base:
        raise SystemExit(f"出力先が outputs/value_audit/ を脱出します: {slug!r}")
    return p


# ---------------------------------------------------------------------------
# 構造化条件 / 必須項目の検証(§2.6・§3)
# ---------------------------------------------------------------------------
def _validate_condition(c: dict, where: str) -> None:
    if not isinstance(c, dict):
        raise SystemExit(f"{where} は object である必要があります")
    if not c.get("metric"):
        raise SystemExit(f"{where}.metric は必須です")
    op = c.get("operator")
    if op not in va.ALLOWED_OPERATORS:
        raise SystemExit(f"{where}.operator が不正: {op!r}(許容 {va.ALLOWED_OPERATORS})")
    try:
        va._check_threshold_type(op, c.get("threshold"))
    except ValueError as e:
        raise SystemExit(f"{where}: {e}")
    tol = c.get("tolerance", 0.0)
    if tol is not None and (not va._finite(tol) or tol < 0):
        raise SystemExit(f"{where}.tolerance は非負の有限数: {tol!r}")


def _nonempty_text(v) -> bool:
    return isinstance(v, str) and v.strip().lower() not in _PLACEHOLDERS and len(v.strip()) >= _MIN_TEXT_LEN


def _scan_forbidden(obj, path="") -> None:
    """禁止フィールドが入力のどこかに無いか再帰チェック(買い意思の混入防止)。"""
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in FORBIDDEN_FIELDS:
                raise SystemExit(f"禁止フィールドが含まれています(買い意思/推奨に見えるため): {path}{k}")
            _scan_forbidden(v, f"{path}{k}.")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            _scan_forbidden(v, f"{path}{i}.")


def load_thesis_input(path: Path) -> dict:
    """register --from-file の入力を検証して返す(必須・禁止・anti_thesis ゲート)。"""
    d = _read_json(path, "仮説入力")
    _scan_forbidden(d)

    validate_ticker(d.get("ticker"))
    for k in ("snapshot_at", "cycle", "valuation", "cheapness_reason",
              "anti_thesis", "falsification", "next_earnings_checklist"):
        if k not in d or d.get(k) in (None, "", [], {}):
            raise SystemExit(f"必須項目がありません: {k}")

    pi = d.get("position_intent", "paper_only")
    if pi not in VALID_POSITION_INTENT:
        raise SystemExit(f"position_intent が不正: {pi!r}(許容 {sorted(VALID_POSITION_INTENT)})")

    cr = d["cheapness_reason"]
    if not isinstance(cr, dict) or cr.get("classification") not in VALID_CHEAPNESS_CLASS:
        raise SystemExit(f"cheapness_reason.classification が不正(許容 {sorted(VALID_CHEAPNESS_CLASS)})")

    at = d["anti_thesis"]
    if not isinstance(at, dict):
        raise SystemExit("anti_thesis は object で必須です")
    for k in ("why_cheap_may_be_deserved", "structural_risk_case", "intensifies_if"):
        if not _nonempty_text(at.get(k)):
            raise SystemExit(f"anti_thesis.{k} は実質的な記述が必須です(空・定型文・短すぎは拒否)")

    fals = d["falsification"]
    if not isinstance(fals, list) or not fals:
        raise SystemExit("falsification は1件以上必須です")
    for i, c in enumerate(fals):
        _validate_condition(c, f"falsification[{i}]")
    cl = d["next_earnings_checklist"]
    if not isinstance(cl, list) or not cl:
        raise SystemExit("next_earnings_checklist は1件以上必須です")
    for i, c in enumerate(cl):
        if c.get("qualitative_only") is True:
            if not c.get("metric"):
                raise SystemExit(f"next_earnings_checklist[{i}].metric は必須です")
            continue
        _validate_condition(c, f"next_earnings_checklist[{i}]")

    cyc = d["cycle"]
    if not isinstance(cyc, dict) or not cyc.get("start_available_at"):
        raise SystemExit("cycle.start_available_at は必須です")
    return d


def load_outcome_input(path: Path) -> dict:
    """score --from-file の入力を検証して返す(手入力 actuals=ASSUMPTION)。"""
    d = _read_json(path, "採点入力")
    _scan_forbidden(d)
    for k in ("thesis_id", "next_earnings_available_at", "entry_price",
              "exit_price", "actuals", "asof", "source"):
        if k not in d or d.get(k) in (None, ""):
            raise SystemExit(f"採点入力に必須項目がありません: {k}")
    if not va._finite(d["entry_price"]) or d["entry_price"] <= 0:
        raise SystemExit("entry_price は正の有限数で必須です")
    if not va._finite(d["exit_price"]) or d["exit_price"] < 0:
        raise SystemExit("exit_price は非負の有限数で必須です")
    if not isinstance(d["actuals"], dict):
        raise SystemExit("actuals は object(metric->値)で必須です")
    return d


# ---------------------------------------------------------------------------
# 追記専用 JSONL I/O
# ---------------------------------------------------------------------------
def _read_json(path: Path, what: str) -> dict:
    if not path.exists():
        raise SystemExit(f"{what} が見つかりません: {path}")
    try:
        d = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise SystemExit(f"{what} の JSON が不正です({path}): {e}")
    if not isinstance(d, dict):
        raise SystemExit(f"{what} は object である必要があります: {path}")
    return d


def _read_jsonl(path: Path, what: str) -> list[dict]:
    if not path.exists():
        return []
    out = []
    for i, ln in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        ln = ln.strip()
        if not ln:
            continue
        try:
            rec = json.loads(ln)
        except json.JSONDecodeError:
            raise SystemExit(f"{what} の {i} 行目が壊れています(JSON不正)。手で修復を: {path}")
        if not isinstance(rec, dict) or "type" not in rec:
            raise SystemExit(f"{what} の {i} 行目に type がありません: {path}")
        out.append(rec)
    return out


def _append_jsonl(path: Path, rec: dict) -> None:
    JOURNAL.mkdir(exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def _now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def read_theses() -> list[dict]:
    return [r for r in _read_jsonl(THESIS_LOG, "value_thesis.jsonl")
            if r.get("type") == "research_item"]


def read_outcomes() -> list[dict]:
    return [r for r in _read_jsonl(OUTCOME_LOG, "value_outcomes.jsonl")
            if r.get("type") == "cycle_outcome"]


def append_thesis(d: dict, asof: str | None) -> str:
    """検証済み仮説を1行追記。event_id/thesis_id/版/時刻/source を付与。"""
    rec = dict(d)
    rec["type"] = "research_item"
    rec["subtype"] = "value_audit"
    rec["schema_version"] = SCHEMA_VERSION
    rec["event_id"] = uuid.uuid4().hex
    rec["created_at"] = _now()
    rec["asof"] = asof
    rec.setdefault("source", "manual")
    rec.setdefault("position_intent", "paper_only")
    rec.setdefault("discipline_status", "未通過")
    if rec.get("amends"):
        if not rec.get("thesis_id"):
            raise SystemExit("amends 指定時は thesis_id(対象の安定 id)が必須です")
    else:
        rec["thesis_id"] = uuid.uuid4().hex[:12]
    _append_jsonl(THESIS_LOG, rec)
    return rec["thesis_id"]


def _outcome_key(rec: dict) -> tuple:
    return (rec.get("thesis_id"), rec.get("cycle_start_available_at"),
            rec.get("next_earnings_available_at"), rec.get("asof"))


def append_outcome(d: dict) -> tuple[str, bool]:
    """採点結果を1行追記(冪等)。同一キーが既存なら追記せず (event_id_or_None, False)。

    返り値: (event_id, written)。written=False は already_scored(重複)。
    訂正は d['amends'] を付ければ別イベントとして追記可能(原本は不変)。
    """
    existing = read_outcomes()
    if not d.get("amends"):
        key = _outcome_key(d)
        for r in existing:
            if _outcome_key(r) == key:
                return (r.get("event_id"), False)  # already_scored
    rec = dict(d)
    rec["type"] = "cycle_outcome"
    rec["schema_version"] = SCHEMA_VERSION
    rec["event_id"] = uuid.uuid4().hex
    rec["outcome_id"] = rec["event_id"]
    rec.setdefault("created_at", _now())
    _append_jsonl(OUTCOME_LOG, rec)
    return (rec["event_id"], True)


# ---------------------------------------------------------------------------
# active_theses(): amends / supersedes の解決(§2.1)
# ---------------------------------------------------------------------------
def active_theses() -> list[dict]:
    """有効版の仮説のみを一意に返す。不正参照・循環・複数有効版・重複 event_id は停止。"""
    recs = read_theses()
    by_event: dict[str, dict] = {}
    for r in recs:
        eid = r.get("event_id")
        if not eid:
            raise SystemExit("value_thesis に event_id が無い行があります")
        if eid in by_event:
            raise SystemExit(f"event_id が重複しています: {eid}")
        by_event[eid] = r

    thesis_ids = {r.get("thesis_id") for r in recs}
    # supersedes: 旧 thesis_id を inactive 化(参照先の存在を検証)
    superseded: set[str] = set()
    for r in recs:
        sup = r.get("supersedes")
        if sup:
            if sup not in thesis_ids:
                raise SystemExit(f"supersedes が存在しない thesis_id を参照: {sup}")
            superseded.add(sup)

    # amends: 参照先 event_id の存在 + 同一 thesis_id + 循環検出
    for r in recs:
        am = r.get("amends")
        if am:
            if am not in by_event:
                raise SystemExit(f"amends が存在しない event_id を参照: {am}")
            if by_event[am].get("thesis_id") != r.get("thesis_id"):
                raise SystemExit(f"amends は同一 thesis_id 内のみ: {r.get('event_id')}")
            # 循環検出
            seen, cur = set(), r
            while cur is not None and cur.get("amends"):
                e = cur.get("event_id")
                if e in seen:
                    raise SystemExit(f"amends が循環しています: {e}")
                seen.add(e)
                cur = by_event.get(cur["amends"])

    actives = []
    by_thesis: dict[str, list[dict]] = {}
    for r in recs:
        by_thesis.setdefault(r.get("thesis_id"), []).append(r)
    for tid, group in by_thesis.items():
        if tid in superseded:
            continue
        # head = どの amends からも参照されていない行(= 鎖の先端)
        amended_targets = {g["amends"] for g in group if g.get("amends")}
        heads = [g for g in group if g.get("event_id") not in amended_targets]
        if len(heads) != 1:
            raise SystemExit(
                f"thesis_id={tid} の有効版が一意に決まりません(分岐/複数有効版)。手修復が必要です")
        actives.append(heads[0])
    return actives
