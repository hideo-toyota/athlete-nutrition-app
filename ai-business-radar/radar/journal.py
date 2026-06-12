"""判断ログ(閉ループの心臓 / 原則2・5・6)。

decision_log.jsonl は**追記専用**。1行=1イベント:
  - type=decision : 反証可能な予測つきの判断(override は理由必須、見送りも記録)
  - type=outcome  : 期日後にツールが機械採点した結果(DCAインデックス超過が hit)
履歴は決して書き換えない。outcome も「別行」で追記する(後知恵の防止)。
score は horizon <= asof かつ記録済み価格のみを使う(未来データ不参照)。
"""
from __future__ import annotations

import json
import math
import uuid
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOG = ROOT / "decision_log.jsonl"

DECISION_FIELDS = ("ticker", "account", "action", "rationale", "prediction",
                   "vs_discipline", "override_reason", "size", "ref_price",
                   "benchmark_ref", "emotion_note")
VALID_ACTIONS = {"buy_new", "add", "trim", "exit", "pass", "hold_review"}


def _read_log() -> list[dict]:
    if not LOG.exists():
        return []
    out = []
    for ln in LOG.read_text(encoding="utf-8").splitlines():
        ln = ln.strip()
        if not ln:
            continue
        try:
            out.append(json.loads(ln))
        except json.JSONDecodeError:
            continue
    return out


def _append(obj: dict) -> None:
    with LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")


def _finite(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)


def append_decision(entry: dict) -> str:
    """判断を1行追記する。反証可能な予測が無ければ拒否。"""
    action = entry.get("action")
    if action not in VALID_ACTIONS:
        raise SystemExit(f"action が不正: {action}(許容: {sorted(VALID_ACTIONS)})")
    pred = entry.get("prediction") or {}
    if not pred.get("claim") or not pred.get("horizon"):
        raise SystemExit("prediction.claim と prediction.horizon は必須"
                         "(反証可能な予測が無い判断は記録しない=原則3/5)")
    if entry.get("vs_discipline") == "override" and not entry.get("override_reason"):
        raise SystemExit("vs_discipline=override の場合は override_reason が必須(原則2)")
    rec = {"type": "decision", "id": str(uuid.uuid4())[:8],
           "ts": datetime.now().isoformat(timespec="seconds")}
    for k in DECISION_FIELDS:
        rec[k] = entry.get(k)
    _append(rec)
    return rec["id"]


def score_due(prices: dict, asof: str | None = None) -> dict:
    """期日到来分を機械採点(DCA超過がhit)。未来・価格欠損はスキップ。"""
    asof = asof or date.today().isoformat()
    log = _read_log()
    decisions = {r["id"]: r for r in log if r.get("type") == "decision"}
    already = {r["id"] for r in log if r.get("type") == "outcome"}
    scored, pending_future, awaiting_price = [], [], []
    for did, d in decisions.items():
        if did in already:
            continue
        horizon = (d.get("prediction") or {}).get("horizon")
        if not horizon or str(horizon) > asof:   # 未来は採点しない(look-ahead回避)
            pending_future.append(did)
            continue
        tk, ref, bref = d.get("ticker"), d.get("ref_price"), d.get("benchmark_ref")
        hp = (prices.get(tk) or {}).get(horizon)
        bhp = (prices.get("BENCHMARK") or {}).get(horizon)
        if not all(_finite(x) for x in (ref, bref, hp, bhp)) or ref == 0 or bref == 0:
            awaiting_price.append(did)
            continue
        ar, br = hp / ref - 1, bhp / bref - 1
        excess = ar - br
        _append({"type": "outcome", "id": did, "scored_at": asof, "horizon": horizon,
                 "asset_return": ar, "benchmark_return": br,
                 "excess_vs_dca": excess, "hit": excess > 0})
        scored.append(did)
    return {"scored": scored, "pending_future": pending_future,
            "awaiting_price": awaiting_price}


def _mean(xs):
    return sum(xs) / len(xs) if xs else None


def review() -> dict:
    """較正(過程>結果): 裁量がDCAに勝てているかを集計。"""
    log = _read_log()
    decisions = [r for r in log if r.get("type") == "decision"]
    outcomes = {r["id"]: r for r in log if r.get("type") == "outcome"}
    scored = [(d, outcomes[d["id"]]) for d in decisions if d["id"] in outcomes]

    def agg(pairs):
        ex = [o["excess_vs_dca"] for _, o in pairs]
        hits = [o["hit"] for _, o in pairs]
        return {"n": len(pairs),
                "hit_rate": (sum(hits) / len(hits)) if hits else None,
                "avg_excess_vs_dca": _mean(ex)}

    by_disc = {}
    for label in ("in_discipline", "override"):
        by_disc[label] = agg([(d, o) for d, o in scored
                              if (d.get("vs_discipline") or "in_discipline") == label])
    return {"n_decisions": len(decisions), "n_scored": len(scored),
            "overall": agg(scored), "by_discipline": by_disc,
            "scored_pairs": scored}
