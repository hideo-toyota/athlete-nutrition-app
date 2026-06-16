#!/usr/bin/env python3
"""
analyze.py — extract_to_csv.py が出力した CSV からトレンドを可視化し、
仮説別のサマリーをテキストで出力する。

使い方:
    python3 analyze.py ./out [-o ./figures]

出力:
    - figures/velocity_trend.png   球速(MAX/AVG)の推移 … H-C
    - figures/recovery_trend.png   安静時HR・睡眠スコア・主観回復 … H-J
    - figures/pain_output.png      投球時痛み と 出力感 … H-G/H-E
    - figures/command.png          1イニング球数・ストライク率(登板) … H-K
    - 標準出力に仮説別サマリー
依存: pandas, matplotlib （pip install pandas matplotlib）
"""
import argparse
import sys
from pathlib import Path

try:
    import pandas as pd
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
except ImportError:
    sys.exit("依存が必要です: pip install pandas matplotlib")


def load(out: Path, name: str):
    p = out / f"{name}.csv"
    if not p.exists():
        return None
    df = pd.read_csv(p)
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df = df.sort_values("date")
    return df


def _save(fig, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(path, dpi=110)
    plt.close(fig)
    print(f"[fig]  {path}")


def plot_velocity(throwing, monthly, fig_dir):
    fig, ax = plt.subplots(figsize=(9, 4))
    plotted = False
    for df, label in ((throwing, "throwing"), (monthly, "monthly")):
        if df is not None and "velo_max" in df:
            sub = df.dropna(subset=["velo_max"])
            if not sub.empty:
                ax.plot(sub["date"], sub["velo_max"], "o-", label=f"max ({label})")
                plotted = True
        if df is not None and "velo_avg" in df:
            sub = df.dropna(subset=["velo_avg"])
            if not sub.empty:
                ax.plot(sub["date"], sub["velo_avg"], "s--", label=f"avg ({label})")
    if plotted:
        ax.set_title("Velocity trend (H-C)")
        ax.set_ylabel("km/h")
        ax.legend()
        _save(fig, fig_dir / "velocity_trend.png")
    else:
        plt.close(fig)


def plot_recovery(daily, fig_dir):
    if daily is None:
        return
    cols = [c for c in ("resting_hr", "sleep_score", "recovery") if c in daily]
    if not cols:
        return
    fig, ax = plt.subplots(figsize=(9, 4))
    for c in cols:
        sub = daily.dropna(subset=[c])
        if not sub.empty:
            ax.plot(sub["date"], sub[c], "o-", label=c)
    ax.set_title("Recovery markers (H-J)")
    ax.legend()
    _save(fig, fig_dir / "recovery_trend.png")


def plot_pain_output(throwing, fig_dir):
    if throwing is None:
        return
    cols = [c for c in ("pain", "output_feel", "next_day_cuff") if c in throwing]
    if not cols:
        return
    fig, ax = plt.subplots(figsize=(9, 4))
    for c in cols:
        sub = throwing.dropna(subset=[c])
        if not sub.empty:
            ax.plot(sub["date"], sub[c], "o-", label=c)
    ax.set_title("Pain / output feel (H-G, H-E, H-D)")
    ax.set_ylabel("0-10")
    ax.legend()
    _save(fig, fig_dir / "pain_output.png")


def plot_command(throwing, fig_dir):
    if throwing is None or "pitches_per_inning" not in throwing:
        return
    games = throwing[throwing.get("session") == "game"].dropna(
        subset=["pitches_per_inning"]
    )
    if games.empty:
        return
    fig, ax = plt.subplots(figsize=(9, 4))
    ax.plot(games["date"], games["pitches_per_inning"], "o-", label="pitches/inning")
    ax.axhline(12, color="green", ls=":", label="CG target 12")
    if "strike_pct" in games:
        ax2 = ax.twinx()
        ax2.plot(games["date"], games["strike_pct"], "s--", color="orange",
                 label="strike %")
        ax2.set_ylabel("strike %")
    ax.set_title("Command efficiency (H-K)")
    ax.set_ylabel("pitches/inning")
    ax.legend(loc="upper left")
    _save(fig, fig_dir / "command.png")


def summary(daily, throwing, monthly):
    print("\n==== 仮説別サマリー ====")
    if throwing is not None and not throwing.empty:
        last = throwing.dropna(subset=["pain"]) if "pain" in throwing else throwing
        if "pain" in throwing:
            painful = throwing[throwing["pain"] > 0].dropna(subset=["pain"])
            if not painful.empty:
                last_pain = painful["date"].max()
                print(f"[H-G] 最後に痛みが出た投球: {last_pain.date()}（以降は無痛継続）")
            else:
                print("[H-G] 記録上、投球時痛み(>0)なし＝無痛継続")
        if "session" in throwing:
            games = throwing[throwing["session"] == "game"]
            if not games.empty and "pitches_per_inning" in games:
                m = games["pitches_per_inning"].dropna().mean()
                print(f"[H-K] 登板の平均1イニング球数: {m:.1f}（目安≤12）")
    if monthly is not None and not monthly.empty:
        for k, label in (("cmj_cm", "CMJ"), ("rmbtv", "RMBTV"),
                         ("velo_max", "球速MAX")):
            if k in monthly:
                s = monthly.dropna(subset=[k])
                if len(s) >= 2:
                    print(f"[H-C] {label}: {s[k].iloc[0]} -> {s[k].iloc[-1]}")
    if daily is not None and "thoracic_drill" in daily:
        rate = daily["thoracic_drill"].fillna(False).astype(bool).mean() * 100
        print(f"[H-B] 胸椎ドリル実施率: {rate:.0f}%")
    print("========================\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out", nargs="?", default="./out", help="CSVフォルダ (既定 ./out)")
    ap.add_argument("-o", "--figures", default="./figures", help="図の出力先")
    args = ap.parse_args()
    out = Path(args.out)
    fig_dir = Path(args.figures)

    daily = load(out, "daily")
    throwing = load(out, "throwing")
    monthly = load(out, "monthly")
    if daily is None and throwing is None and monthly is None:
        sys.exit(f"CSVが見つかりません（先に extract_to_csv.py を実行）: {out}")

    plot_velocity(throwing, monthly, fig_dir)
    plot_recovery(daily, fig_dir)
    plot_pain_output(throwing, fig_dir)
    plot_command(throwing, fig_dir)
    summary(daily, throwing, monthly)


if __name__ == "__main__":
    main()
