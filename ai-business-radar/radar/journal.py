"""判断ログ(閉ループの心臓 / 原則2・5・6)。

decision_log.jsonl は**追記専用・イベントソース**。1行=1イベント:
  - type=decision : 反証可能な予測つきの判断(override は理由必須、見送りも記録)
  - type=outcome  : 期日後にツールが機械採点した結果(買い/売り/見送りの判断方向で hit)
履歴は決して書き換えない。outcome も「別行」で追記する(後知恵の防止)。
score は horizon <= asof(厳密 YYYY-MM-DD)かつ記録済み価格のみを使う(未来データ不参照)。
ログ品質=閉ループ品質。入力検証・破損検知・型検証を厳格に行う。
"""
from __future__ import annotations

import json
import math
import re
import uuid
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOG = ROOT / "decision_log.jsonl"

DECISION_FIELDS = ("ticker", "account", "action", "rationale", "prediction",
                   "vs_discipline", "override_reason", "size", "ref_price",
                   "benchmark_ref", "emotion_note", "sources", "retrieved_at")
VALID_ACTIONS = {"buy_new", "add", "trim", "exit", "pass", "hold_review"}
SCOREABLE_ACTIONS = {"buy_new", "add", "trim", "exit", "pass"}  # hold_review は採点しない
LONG_DECISIONS = {"buy_new", "add"}
AVOID_DECISIONS = {"trim", "exit", "pass"}
VALID_DISCIPLINE = {"in_discipline", "override"}
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _finite(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)


def _date(s):
    """厳密に 'YYYY-MM-DD'(実在日)のみ受理。20260131 / 2026-W05-6 / 2026-02 / 2026-02-31 は None。"""
    if not isinstance(s, str) or not _DATE_RE.match(s):
        return None
    try:
        return date.fromisoformat(s)
    except ValueError:
        return None


def _read_log() -> list[dict]:
    """追記専用ログを読む。破損行・型不正は黙殺せず停止(ファイル=真実)。"""
    if not LOG.exists():
        return []
    out = []
    for i, ln in enumerate(LOG.read_text(encoding="utf-8").splitlines(), 1):
        ln = ln.strip()
        if not ln:
            continue
        try:
            rec = json.loads(ln)
        except json.JSONDecodeError:
            raise SystemExit(f"decision_log.jsonl の {i} 行目が壊れています(JSON不正)。手で修復を。")
        if not isinstance(rec, dict) or "type" not in rec:
            raise SystemExit(f"decision_log.jsonl の {i} 行目に type がありません")
        if rec["type"] == "outcome":
            for k in ("id", "excess_vs_dca", "hit"):
                if k not in rec:
                    raise SystemExit(f"decision_log.jsonl の {i} 行目(outcome)に {k} がありません")
            if not _finite(rec["excess_vs_dca"]):
                raise SystemExit(f"decision_log.jsonl の {i} 行目(outcome): excess_vs_dca が数値でない")
            if "decision_excess_vs_dca" in rec and not _finite(rec["decision_excess_vs_dca"]):
                raise SystemExit(f"decision_log.jsonl の {i} 行目(outcome): decision_excess_vs_dca が数値でない")
            if "score_direction" in rec and rec["score_direction"] not in {"long", "avoid"}:
                raise SystemExit(f"decision_log.jsonl の {i} 行目(outcome): score_direction が不正")
            if not isinstance(rec["hit"], bool):
                raise SystemExit(f"decision_log.jsonl の {i} 行目(outcome): hit が真偽値でない")
        elif rec["type"] == "decision" and "id" not in rec:
            raise SystemExit(f"decision_log.jsonl の {i} 行目(decision)に id がありません")
        out.append(rec)
    return out


def _append(obj: dict) -> None:
    with LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")


def _decision_score(action: str, excess: float) -> tuple[str, float, bool]:
    """判断方向に合わせたDCA比の成否。

    buy/add は対象がDCAを上回れば成功。trim/exit/pass は、その後に対象がDCAを
    下回れば「避けた判断」として成功。rawな excess_vs_dca は監査用に別途残す。
    """
    if action in LONG_DECISIONS:
        return "long", excess, bool(excess > 0)
    if action in AVOID_DECISIONS:
        return "avoid", -excess, bool(excess < 0)
    raise SystemExit(f"採点対象外の action です: {action}")


def append_decision(entry: dict) -> str:
    """判断を1行追記する。品質検証(予測・必須項目・型・有限/正)を満たさなければ拒否。"""
    if not isinstance(entry, dict):
        raise SystemExit("判断入力は object である必要があります")
    action = entry.get("action")
    if action not in VALID_ACTIONS:
        raise SystemExit(f"action が不正: {action}(許容: {sorted(VALID_ACTIONS)})")
    for k in ("ticker", "rationale"):
        if not entry.get(k):
            raise SystemExit(f"{k} は必須です")
    pred = entry.get("prediction")
    if not isinstance(pred, dict):
        raise SystemExit("prediction は object で必須")
    if not pred.get("claim"):
        raise SystemExit("prediction.claim は必須(反証可能な予測が無い判断は記録しない)")
    if not _date(pred.get("horizon")):
        raise SystemExit("prediction.horizon は実在する 'YYYY-MM-DD' で必須")
    vs = entry.get("vs_discipline") or "in_discipline"
    if vs not in VALID_DISCIPLINE:
        raise SystemExit(f"vs_discipline が不正: {vs}(許容: {sorted(VALID_DISCIPLINE)})")
    if vs == "override" and not entry.get("override_reason"):
        raise SystemExit("vs_discipline=override の場合は override_reason が必須(原則2)")
    if action != "hold_review":
        for k in ("ref_price", "benchmark_ref"):
            v = entry.get(k)
            if not _finite(v) or v <= 0:
                raise SystemExit(f"{k} は正の有限数で必須(採点に必要)")
    size = entry.get("size")
    if size is not None:
        if not isinstance(size, dict):
            raise SystemExit("size は object である必要があります")
        amt = size.get("amount_jpy")
        if amt is not None and (not _finite(amt) or amt < 0):
            raise SystemExit("size.amount_jpy は非負の有限数で指定してください")
    # 監査証跡(任意だが推奨): どの出典を・いつ取得して判断したか
    src = entry.get("sources")
    if src is not None and not isinstance(src, list):
        raise SystemExit("sources は配列(出典URL/名のリスト)である必要があります")
    ra = entry.get("retrieved_at")
    if ra is not None and not (isinstance(ra, str) and ra.strip()):
        raise SystemExit("retrieved_at は非空の文字列(ISO日時)である必要があります")

    rec = {"type": "decision", "id": str(uuid.uuid4())[:12],
           "ts": datetime.now().astimezone().isoformat(timespec="seconds")}
    for k in DECISION_FIELDS:
        rec[k] = entry.get(k)
    rec["vs_discipline"] = vs
    _append(rec)
    return rec["id"]


def score_due(prices: dict, asof: str | None = None) -> dict:
    """期日到来分を機械採点。未来・価格欠損・型不正・hold_reviewはスキップ。

    buy/add は対象がDCAを上回れば hit。trim/exit/pass は対象がDCAを下回れば hit。
    """
    if not isinstance(prices, dict):
        raise SystemExit("価格データは object である必要があります")
    if asof is None:
        raise SystemExit("asof は必須です。監査再現性のため 'YYYY-MM-DD' で明示してください")
    asof_d = _date(asof)
    if asof_d is None:
        raise SystemExit(f"asof は実在する 'YYYY-MM-DD' で指定してください: {asof}")

    log = _read_log()
    decisions = {r["id"]: r for r in log if r.get("type") == "decision"}
    already = {r["id"] for r in log if r.get("type") == "outcome"}
    scored, pending_future, awaiting_price = [], [], []
    for did, d in decisions.items():
        if did in already or d.get("action") not in SCOREABLE_ACTIONS:
            continue
        pred = d.get("prediction")
        pred = pred if isinstance(pred, dict) else {}   # 旧/手編集ログ防御
        hd = _date(pred.get("horizon"))
        if hd is None or hd > asof_d:   # 未来/不正日付は採点しない(look-ahead回避)
            pending_future.append(did)
            continue
        horizon = pred.get("horizon")
        tk, ref, bref = d.get("ticker"), d.get("ref_price"), d.get("benchmark_ref")
        tkp, bp = prices.get(tk), prices.get("BENCHMARK")
        if not isinstance(tkp, dict) or not isinstance(bp, dict):
            awaiting_price.append(did)
            continue
        hp, bhp = tkp.get(horizon), bp.get(horizon)
        if not all(_finite(x) for x in (ref, bref, hp, bhp)) or ref == 0 or bref == 0:
            awaiting_price.append(did)
            continue
        ar, br = hp / ref - 1, bhp / bref - 1
        excess = ar - br
        direction, decision_excess, hit = _decision_score(d.get("action"), excess)
        _append({"type": "outcome", "id": did, "scored_at": asof_d.isoformat(),
                 "horizon": horizon, "asset_return": ar, "benchmark_return": br,
                 "excess_vs_dca": excess,
                 "decision_excess_vs_dca": decision_excess,
                 "score_direction": direction,
                 "hit": hit})
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
        ex = [o.get("decision_excess_vs_dca", o["excess_vs_dca"]) for _, o in pairs]
        raw_ex = [o["excess_vs_dca"] for _, o in pairs]
        hits = [bool(o["hit"]) for _, o in pairs]
        return {"n": len(pairs),
                "hit_rate": (sum(hits) / len(hits)) if hits else None,
                "avg_excess_vs_dca": _mean(ex),
                "avg_raw_excess_vs_dca": _mean(raw_ex)}

    by_disc = {}
    for label in ("in_discipline", "override"):
        by_disc[label] = agg([(d, o) for d, o in scored
                              if (d.get("vs_discipline") or "in_discipline") == label])
    return {"n_decisions": len(decisions), "n_scored": len(scored),
            "overall": agg(scored), "by_discipline": by_disc, "scored_pairs": scored}
