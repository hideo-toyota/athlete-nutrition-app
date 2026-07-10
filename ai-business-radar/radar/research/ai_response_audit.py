"""Local audit for AI-generated investment analysis.

This module does not call an LLM. It turns an AI response into a bounded,
deterministic review packet so the human operator can see weak evidence,
implicit assumptions, logical leaps, and adoption risk before using the answer.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from .common import (
    DISCLAIMER,
    FORBIDDEN_OUTPUT_PATTERNS,
    FORBIDDEN_OUTPUT_TOKENS,
    ROOT,
    assert_no_forbidden_output,
)
from radar.sources.common import redact

EVIDENCE_CLASSES = {
    "A": "一次資料/PIT derived FACT",
    "B": "再現可能検証/backtest/decision log",
    "C": "観察データ/過去相関/統計分析",
    "D": "公的機関/取引所/企業公式見解",
    "E": "専門家/アナリスト/報道の見解",
    "F": "推論/仮説/予想",
    "G": "根拠不明",
}

WEAK_CLASSES = {"E", "F", "G"}

_SPLIT_RE = re.compile(r"(?<=[。！？!?])\s+|\n+")
_BULLET_RE = re.compile(r"^\s*(?:[-*・]|\d+[.)]|#{1,6})\s*")
_WHITESPACE_RE = re.compile(r"\s+")

_INFERENCE_RE = re.compile(
    r"可能性|仮説|推測|考えられる|見込み|予想|だろう|と思う|示唆|判断|シナリオ|期待",
    re.IGNORECASE,
)
_PRIMARY_RE = re.compile(
    r"EDINET|J-Quants|FACT|CALCULATION|有価証券報告書|決算短信|TDnet|"
    r"derived|provenance|raw_hash|asof|price_date|source_date",
    re.IGNORECASE,
)
_REPRO_RE = re.compile(
    r"backtest|out-of-sample|decision_log|score|review|再現|検証済|冪等|追記専用",
    re.IGNORECASE,
)
_OBS_RE = re.compile(
    r"過去|相関|分布|中央値|median|p10|p90|mismatch|リターン|統計|観察|推移",
    re.IGNORECASE,
)
_OFFICIAL_RE = re.compile(
    r"金融庁|東証|JPX|日本取引所|企業公式|会社発表|規制当局|公的機関",
    re.IGNORECASE,
)
_EXPERT_RE = re.compile(
    r"専門家|アナリスト|新聞|報道|記事|レポート|ストラテジスト|証券会社",
    re.IGNORECASE,
)

_CAUSAL_RE = re.compile(r"だから|ため|ので|により|原因|結果として|押し上げ|押し下げ")
_CORRELATION_RE = re.compile(r"相関|連動|同時|一致|分布|過去")
_GENERAL_RE = re.compile(r"必ず|常に|すべて|絶対|誰でも|例外なく")
_STRONG_RE = re.compile(r"確実|間違いない|断定|不可避|勝てる|失敗しない|保証")
_COUNTER_RE = re.compile(r"反証|リスク|UNKNOWN|ただし|一方|例外|弱点|未確認|不足")
_CONCLUSION_RE = re.compile(r"結論|したがって|ゆえに|採用|使える|判断")


def _normalize(text: str) -> str:
    return _WHITESPACE_RE.sub(" ", str(text or "")).strip()


def _safe_excerpt(text: str, *, limit: int = 160) -> str:
    out = redact(_normalize(text))
    for token in FORBIDDEN_OUTPUT_TOKENS:
        out = re.sub(re.escape(token), "[禁止語]", out, flags=re.IGNORECASE)
    for pattern in FORBIDDEN_OUTPUT_PATTERNS:
        out = pattern.sub("[禁止表現]", out)
    return out[:limit] + ("..." if len(out) > limit else "")


def _sentences(text: str, *, max_claims: int) -> list[str]:
    candidates: list[str] = []
    for chunk in _SPLIT_RE.split(text):
        chunk = _BULLET_RE.sub("", chunk).strip()
        if not chunk:
            continue
        # Split long markdown lines on Japanese full stops when they were not
        # followed by whitespace.
        parts = [p.strip() for p in re.split(r"(?<=。)", chunk) if p.strip()]
        for part in parts:
            clean = _normalize(part)
            if len(clean) >= 18:
                candidates.append(clean)
        if len(candidates) >= max_claims:
            break
    return candidates[:max_claims]


def _classify_claim(sentence: str) -> tuple[str, str]:
    if _INFERENCE_RE.search(sentence):
        return "F", "予想・仮説・示唆を含むため"
    if _PRIMARY_RE.search(sentence):
        return "A", "一次資料/PIT派生値/claimタグへの参照を含むため"
    if _REPRO_RE.search(sentence):
        return "B", "再現可能な検証ログやbacktestへの参照を含むため"
    if _OBS_RE.search(sentence):
        return "C", "過去データ・分布・統計への参照を含むため"
    if _OFFICIAL_RE.search(sentence):
        return "D", "公的/公式主体への参照を含むため"
    if _EXPERT_RE.search(sentence):
        return "E", "外部専門家・報道の見解への依存を含むため"
    return "G", "根拠種別を本文から判別できないため"


def _claim_audit(sentences: list[str]) -> list[dict]:
    claims = []
    for i, s in enumerate(sentences, start=1):
        cls, reason = _classify_claim(s)
        claims.append({
            "id": f"C{i:02d}",
            "excerpt": _safe_excerpt(s),
            "evidence_class": cls,
            "evidence_label": EVIDENCE_CLASSES[cls],
            "reason": reason,
            "weak": cls in WEAK_CLASSES,
        })
    return claims


def _assumption_audit() -> list[dict]:
    assumptions = [
        (
            "入力されたAI回答に、判断に必要な根拠が欠落なく含まれている",
            "本文外の出典や数表に依存している場合、根拠分類はG寄りに倒す必要がある",
        ),
        (
            "回答内の数値はPIT/asofに沿っている",
            "未来データが混入していれば、採用判定は一段以上下げる",
        ),
        (
            "AI回答は売買指示ではなく調査補助である",
            "売買指示に滑っていれば、この監査結果ごと人間レビューに差し戻す",
        ),
        (
            "読み手はdiscipline checkを別途通す",
            "規律ゲートを省く運用なら、どれだけ根拠が強くても使い方を制限する",
        ),
        (
            "derived featuresとevidence packは最新かつ壊れていない",
            "データ鮮度やcoverageに問題があれば、結論よりデータ修復を優先する",
        ),
        (
            "UNKNOWNが0や安全側の数値に変換されていない",
            "UNKNOWNが潰れていれば、分析の不確実性が過小評価される",
        ),
        (
            "短い文章からでも主要な論理飛躍を検出できる",
            "長い根拠表を省略した回答では、監査は保守的にしか使えない",
        ),
        (
            "過去の分布や相関は、仮説検証の入口としてだけ使う",
            "因果や将来成績に読み替えると、結論は弱くなる",
        ),
        (
            "LLM入力・出力の利用条件は本人確認済みの私的利用内に収まる",
            "外部共有や再配布が混じるなら、運用ゲートを止める",
        ),
        (
            "監査済みという事実は、正しさの保証ではない",
            "同じ誤りをAI同士が共有する可能性があるため、人間判断は残す",
        ),
    ]
    return [
        {"id": f"A{i:02d}", "assumption": a, "if_broken": impact}
        for i, (a, impact) in enumerate(assumptions, start=1)
    ]


def _logic_audit(sentences: list[str], claims: list[dict]) -> list[dict]:
    leaps = []
    for s in sentences:
        if _CAUSAL_RE.search(s) and _CORRELATION_RE.search(s):
            leaps.append({
                "type": "相関と因果の混同",
                "severity": "中",
                "excerpt": _safe_excerpt(s),
                "why": "相関・同時変化から原因を推定している可能性",
            })
        if _GENERAL_RE.search(s):
            leaps.append({
                "type": "過剰一般化",
                "severity": "中",
                "excerpt": _safe_excerpt(s),
                "why": "例外を許さない語が含まれる",
            })
        if _STRONG_RE.search(s):
            leaps.append({
                "type": "結論の強すぎる表現",
                "severity": "高",
                "excerpt": _safe_excerpt(s),
                "why": "投資分析として断定が強すぎる",
            })
    text = " ".join(sentences)
    if sentences and not _COUNTER_RE.search(text):
        leaps.append({
            "type": "反対事例の無視",
            "severity": "中",
            "excerpt": "回答全体",
            "why": "反証・リスク・UNKNOWN・例外への言及が見当たらない",
        })
    weak_count = sum(1 for c in claims if c["weak"])
    if weak_count >= 3 and _CONCLUSION_RE.search(text):
        leaps.append({
            "type": "前提と結論のズレ",
            "severity": "高",
            "excerpt": "回答全体",
            "why": "根拠が弱い主張が多い一方で、採用/結論に寄った表現がある",
        })
    return leaps[:12]


def _context_audit(*, purpose: str, audience: str, constraints: str, avoid: str,
                   claims: list[dict], leaps: list[dict]) -> dict:
    weak_count = sum(1 for c in claims if c["weak"])
    high_leaps = sum(1 for l in leaps if l.get("severity") == "高")
    useful = [
        "回答の主張を根拠種別ごとに分解できる",
        "暗黙前提と反証観点を人間判断の前に確認できる",
    ]
    misfit = []
    if weak_count:
        misfit.append(f"根拠が弱い主張が {weak_count} 件あるため、結論部分はそのまま使いにくい")
    if high_leaps:
        misfit.append(f"重要な論理飛躍が {high_leaps} 件あるため、追加確認が必要")
    if not misfit:
        misfit.append("大きなズレは検出されないが、監査は正しさの保証ではない")
    return {
        "purpose": purpose,
        "audience": audience,
        "constraints": constraints,
        "avoid": avoid,
        "usable_parts": useful,
        "misfit_parts": misfit,
    }


def _counterarguments(claims: list[dict], leaps: list[dict]) -> list[dict]:
    weak = [c for c in claims if c["weak"]]
    args = []
    if weak:
        args.append({
            "point": "根拠の弱い主張が結論を支えている",
            "failure_mode": "根拠不明や推論が中心なら、分析がもっともらしい物語に寄る",
            "check": "A/B/C/Dの根拠に置き換えられるか確認する",
        })
    if leaps:
        args.append({
            "point": "論理飛躍が残っている",
            "failure_mode": "相関や短期変化を、構造的な優位性や将来成績に読み替える",
            "check": "反証条件と逆シナリオを先に書く",
        })
    args.append({
        "point": "UNKNOWNが投資判断上の盲点になりうる",
        "failure_mode": "未取得データや定義差を無視して、確信度を過大評価する",
        "check": "UNKNOWN一覧と次に読む資料を決めてから判断する",
    })
    args.append({
        "point": "AI同士の監査でも同じ誤りを共有しうる",
        "failure_mode": "監査済みというラベルが過信につながる",
        "check": "最終判断はdiscipline checkと人間判断に残す",
    })
    return args[:3]


def _forbidden_hit_count(text: str) -> int:
    normalized = _normalize(text)
    count = sum(1 for t in FORBIDDEN_OUTPUT_TOKENS if t in normalized)
    count += sum(1 for p in FORBIDDEN_OUTPUT_PATTERNS if p.search(normalized))
    return count


def _adoption_judgement(*, claims: list[dict], leaps: list[dict], forbidden_hits: int) -> dict:
    weak_count = sum(1 for c in claims if c["weak"])
    high_leaps = sum(1 for l in leaps if l.get("severity") == "高")
    if forbidden_hits:
        level = 4
        label = "使わないほうがいい"
        reason = "売買指示や価格目標に近い禁止表現が含まれるため"
    elif weak_count >= 6 or high_leaps >= 2:
        level = 3
        label = "参考程度にとどめる"
        reason = "根拠の弱さまたは重要な論理飛躍が多いため"
    elif weak_count or leaps:
        level = 2
        label = "一部修正すれば使える"
        reason = "使える材料はあるが、根拠補強・前提確認・反証追加が必要なため"
    else:
        level = 1
        label = "そのまま使える"
        reason = "弱い根拠や主要な論理飛躍が検出されないため"
    return {"level": level, "label": label, "reason": reason}


def build_ai_response_audit(*, response_text: str, source_name: str = "stdin",
                            purpose: str = "投資判断前のAI回答品質監査",
                            audience: str = "個人投資家本人",
                            constraints: str = "売買指示なし・PIT・claim分類・discipline gate維持",
                            avoid: str = "AI回答の過信、根拠不明の断定、買い煽り化",
                            max_claims: int = 20) -> dict:
    if not isinstance(response_text, str) or not response_text.strip():
        raise SystemExit("ai-audit: 入力テキストが空です")
    if max_claims <= 0:
        raise SystemExit("--max-claims は正の整数で指定してください")
    source_hash = hashlib.sha256(response_text.encode("utf-8")).hexdigest()
    sentences = _sentences(response_text, max_claims=max_claims)
    claims = _claim_audit(sentences)
    leaps = _logic_audit(sentences, claims)
    forbidden_hits = _forbidden_hit_count(response_text)
    weak = [c for c in claims if c["weak"]]
    return {
        "schema_version": "1",
        "source_name": source_name,
        "source_sha256": source_hash,
        "source_text_included": False,
        "llm_api_called": False,
        "audit_method": "deterministic_local_rules",
        "claim_audit": {
            "evidence_classes": EVIDENCE_CLASSES,
            "claims": claims,
            "weak_claims": weak,
        },
        "assumption_audit": _assumption_audit(),
        "logic_audit": leaps,
        "context_audit": _context_audit(
            purpose=purpose,
            audience=audience,
            constraints=constraints,
            avoid=avoid,
            claims=claims,
            leaps=leaps,
        ),
        "counterarguments": _counterarguments(claims, leaps),
        "adoption": _adoption_judgement(
            claims=claims,
            leaps=leaps,
            forbidden_hits=forbidden_hits,
        ),
        "guardrails": {
            "forbidden_hit_count_in_source": forbidden_hits,
            "full_source_not_rendered": True,
            "discipline_gate_required": True,
        },
    }


def render_ai_response_audit(audit: dict) -> str:
    claim_audit = audit.get("claim_audit") or {}
    claims = claim_audit.get("claims") or []
    weak = claim_audit.get("weak_claims") or []
    leaps = audit.get("logic_audit") or []
    adoption = audit.get("adoption") or {}
    ctx = audit.get("context_audit") or {}
    out = [
        "# AI Response Audit — 回答品質監査",
        "",
        f"_source: `{audit.get('source_name')}` / source_sha256: `{audit.get('source_sha256')}`_",
        "",
        f"> {DISCLAIMER}",
        "",
        "## 0. Boundary",
        "- 外部LLM APIは呼んでいません。",
        "- 入力全文は保存せず、短い抜粋だけを監査用に保持します。",
        "- この監査は正しさの保証ではなく、根拠不足・前提・論理飛躍を見つけるための道具です。",
        "- 最終判断は人間。売買を考える場合も discipline check が必要です。",
        "",
        "## 1. 採用判定",
        f"- 判定: `{adoption.get('level')}. {adoption.get('label')}`",
        f"- 理由: {adoption.get('reason')}",
        f"- 入力内の禁止表現検出数: {audit.get('guardrails', {}).get('forbidden_hit_count_in_source', 0)}",
        "",
        "## 2. 根拠分類",
        "| id | class | weak | excerpt | reason |",
        "|---|---|---:|---|---|",
    ]
    for c in claims:
        out.append(
            f"| {c['id']} | {c['evidence_class']} {c['evidence_label']} | "
            f"{'yes' if c['weak'] else 'no'} | {c['excerpt']} | {c['reason']} |"
        )
    out.extend([
        "",
        "## 3. 根拠が弱い主張",
    ])
    if weak:
        for c in weak:
            out.append(f"- {c['id']}: {c['excerpt']} ({c['evidence_class']})")
    else:
        out.append("- 検出なし")
    out.extend([
        "",
        "## 4. 暗黙の前提と崩れた場合",
        "| id | assumption | if broken |",
        "|---|---|---|",
    ])
    for a in audit.get("assumption_audit") or []:
        out.append(f"| {a['id']} | {a['assumption']} | {a['if_broken']} |")
    out.extend([
        "",
        "## 5. 論理飛躍チェック",
    ])
    if leaps:
        out.extend(["| type | severity | excerpt | why |", "|---|---|---|---|"])
        for leap in leaps:
            out.append(
                f"| {leap['type']} | {leap['severity']} | {leap['excerpt']} | {leap['why']} |"
            )
    else:
        out.append("- 検出なし")
    out.extend([
        "",
        "## 6. 文脈適合",
        f"- purpose: {ctx.get('purpose')}",
        f"- audience: {ctx.get('audience')}",
        f"- constraints: {ctx.get('constraints')}",
        f"- avoid: {ctx.get('avoid')}",
        "- 使える部分:",
    ])
    out.extend(f"  - {x}" for x in ctx.get("usable_parts") or [])
    out.append("- ズレ/注意:")
    out.extend(f"  - {x}" for x in ctx.get("misfit_parts") or [])
    out.extend([
        "",
        "## 7. 最強の反論",
    ])
    for i, arg in enumerate(audit.get("counterarguments") or [], start=1):
        out.extend([
            f"### {i}. {arg['point']}",
            f"- failure_mode: {arg['failure_mode']}",
            f"- check: {arg['check']}",
        ])
    out.append("")
    text = "\n".join(out)
    assert_no_forbidden_output(text)
    return text


def _safe_output_stem(source_name: str) -> str:
    name = Path(source_name).stem or "ai_response"
    stem = re.sub(r"[^0-9A-Za-z._-]+", "_", name).strip("._-")
    return stem[:80] or "ai_response"


def write_ai_response_audit(audit: dict, *, outputs_root: Path | None = None,
                            output_name: str | None = None) -> dict:
    root = outputs_root or (ROOT / "outputs")
    out_dir = root / "ai_audit"
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = _safe_output_stem(output_name or audit.get("source_name") or "ai_response")
    md = out_dir / f"{stem}.md"
    manifest = out_dir / f"{stem}.json"
    md.write_text(render_ai_response_audit(audit), encoding="utf-8")
    manifest.write_text(json.dumps(audit, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {
        "md_path": md,
        "manifest_path": manifest,
        "adoption_level": (audit.get("adoption") or {}).get("level"),
        "weak_claim_count": len(((audit.get("claim_audit") or {}).get("weak_claims") or [])),
        "logic_leap_count": len(audit.get("logic_audit") or []),
    }
