"""CLI(MVP: mirror)。実行: `python3 -m radar mirror`(ai-business-radar/ で)。"""
from __future__ import annotations

import argparse
from pathlib import Path

from .concentration import look_through
from .config import load_config
from .data import load_portfolio
from .report import render_mirror

ROOT = Path(__file__).resolve().parent.parent
OUTPUTS = ROOT / "outputs"


def cmd_mirror() -> None:
    cfg = load_config()
    pf = load_portfolio()
    exp = look_through(pf, cfg)
    OUTPUTS.mkdir(exist_ok=True)
    out = OUTPUTS / "honest_mirror.md"
    out.write_text(render_mirror(exp, pf, cfg), encoding="utf-8")
    lt = exp["lookthrough"]
    print(f"honest mirror を生成しました: {out.relative_to(ROOT)}")
    print(f"  実質 US-Tech/AI: {lt['by_sector'].get('US-Tech/AI', 0):.0f}%"
          f" / USD: {lt['by_currency'].get('USD', 0):.0f}%"
          f" / 個別株: {exp['satellite']['individual_pct']:.1f}%"
          + ("  ⚠️上限超過あり" if (exp['satellite']['over_total_cap']
             or exp['satellite']['name_breaches']
             or exp['satellite']['sector_breaches']) else ""))


def _todo(name: str) -> None:
    print(f"`{name}` は未実装(PLAN: Phase 2以降)。MVPは `mirror` から。")


def main() -> None:
    ap = argparse.ArgumentParser(prog="radar",
                                 description="Personal Equity Research Radar")
    sub = ap.add_subparsers(dest="command")
    sub.add_parser("mirror", help="正直な集中度レポート(look-through)")
    for later in ("check", "log", "score", "review"):
        sub.add_parser(later, help=f"(未実装 / PLAN後段) {later}")
    args = ap.parse_args()

    if args.command == "mirror":
        cmd_mirror()
    elif args.command in ("check", "log", "score", "review"):
        _todo(args.command)
    else:
        ap.print_help()


if __name__ == "__main__":
    main()
