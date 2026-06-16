#!/usr/bin/env python3
"""
extract_to_csv.py — Obsidian vault の投球記録(Markdown+YAMLフロントマター)を
type 別に CSV へ抽出する。

使い方:
    python3 extract_to_csv.py /path/to/vault [-o ./out]

仕様:
    - 再帰的に .md を走査し、先頭の YAML フロントマター(--- ... ---)を読む。
    - フロントマターに `type` があり daily/throwing/monthly のいずれかなら対象。
    - daily.csv / throwing.csv / monthly.csv を出力（フィールドの和集合を列に）。
    - 派生指標も付与: ストライク率(strike_pct)・1イニング球数(pitches_per_inning)。
依存: pyyaml （pip install pyyaml）
"""
import argparse
import csv
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.exit("pyyaml が必要です: pip install pyyaml")

TYPES = ("daily", "throwing", "monthly")


def parse_frontmatter(text: str):
    """先頭の --- ... --- を辞書で返す。無ければ None。"""
    if not text.startswith("---"):
        return None
    end = text.find("\n---", 3)
    if end == -1:
        return None
    block = text[3:end].strip("\n")
    try:
        data = yaml.safe_load(block)
    except yaml.YAMLError:
        return None
    return data if isinstance(data, dict) else None


def derive(row: dict) -> dict:
    """派生指標を追加（投球・登板向け）。"""
    pc = row.get("pitch_count")
    strikes = row.get("strikes")
    innings = row.get("innings")
    try:
        if pc and strikes:
            row["strike_pct"] = round(float(strikes) / float(pc) * 100, 1)
    except (ValueError, ZeroDivisionError, TypeError):
        pass
    try:
        if pc and innings:
            row["pitches_per_inning"] = round(float(pc) / float(innings), 1)
    except (ValueError, ZeroDivisionError, TypeError):
        pass
    return row


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("vault", help="Obsidian vault（または記録フォルダ）のパス")
    ap.add_argument("-o", "--out", default="./out", help="CSV出力先 (既定: ./out)")
    args = ap.parse_args()

    vault = Path(args.vault)
    if not vault.exists():
        sys.exit(f"パスが存在しません: {vault}")
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    buckets = {t: [] for t in TYPES}
    for md in vault.rglob("*.md"):
        try:
            fm = parse_frontmatter(md.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError):
            continue
        if not fm:
            continue
        t = str(fm.get("type", "")).strip()
        if t in TYPES:
            fm["_file"] = str(md.relative_to(vault))
            buckets[t].append(derive(fm) if t == "throwing" else fm)

    for t, rows in buckets.items():
        if not rows:
            print(f"[skip] {t}: 0 件")
            continue
        cols = []
        for r in rows:
            for k in r:
                if k not in cols:
                    cols.append(k)
        rows.sort(key=lambda r: str(r.get("date", "")))
        path = out / f"{t}.csv"
        with path.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=cols)
            w.writeheader()
            w.writerows(rows)
        print(f"[ok]   {t}: {len(rows)} 件 -> {path}")


if __name__ == "__main__":
    main()
