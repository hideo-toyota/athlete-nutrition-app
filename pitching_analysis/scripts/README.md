# scripts — 集計・可視化

Obsidianの投球記録（Markdown＋YAMLフロントマター）を、相関分析・グラフ・他AI共有のために CSV/図へ変換するツール。

> 日々のトレンドは Obsidian の **Dataviewダッシュボード**（`templates/dashboard.md`）で十分見られます。これらのスクリプトは、より踏み込んだ分析・グラフ化・バックアップが必要なときに使います。

## セットアップ

```bash
pip install -r requirements.txt
```

## 使い方

```bash
# 1) vault から CSV を抽出（daily.csv / throwing.csv / monthly.csv）
python3 extract_to_csv.py /path/to/your/vault -o ./out

# 2) トレンドを可視化＋仮説別サマリーを表示
python3 analyze.py ./out -o ./figures
```

このリポジトリの `examples/` でも試せます:

```bash
python3 extract_to_csv.py ../examples -o ./out
python3 analyze.py ./out -o ./figures
```

## 出力

- `out/daily.csv`, `out/throwing.csv`, `out/monthly.csv`
- `figures/velocity_trend.png`（H-C）, `recovery_trend.png`（H-J）, `pain_output.png`（H-G/E/D）, `command.png`（H-K）
- 標準出力に仮説別サマリー（無痛継続・1イニング球数・CMJ/RMBTV/球速の起点比・胸椎ドリル実施率）

## 備考

- フロントマターの `type`（daily/throwing/monthly）と日付命名規則に依存します。
- 空欄（未記入）は自動でスキップされるので、埋まっていない項目があっても動きます。
- 列はファイル群のフィールドの和集合。新しい項目を足しても壊れません。
