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

## 動画解析（video_pose.py）

投球動画を MediaPipe Pose で解析し、関節角の時系列CSV＋骨格を重ねた注釈動画を出力します。

```bash
pip install mediapipe opencv-python numpy
python3 video_pose.py input.mp4 --hand right --view rear -o ./out_video
```

- `--hand right/left`：投球腕（踏み出し脚は反対側を自動選択）
- `--view side/rear/face`：撮影視点（分離角はrear/face、ブロック/前傾はsideが読みやすい）
- `--slowmo 3`：スロー版(1/3速)も出力（既定3、`0`で無効。ffmpeg必須）
- 出力：`out_video/annotated.mp4`（骨格＋角度オーバーレイ。**ffmpegがあればH.264で再生互換**、無ければmp4v）、`annotated_slow.mp4`（スロー版）、`out_video/pose_metrics.csv`（分離角・前脚膝角・体幹傾斜・腕スロットの時系列）、極値サマリー（最大分離角・最小膝角）

> 再生互換のため `ffmpeg` の導入を推奨（`apt install ffmpeg` / `brew install ffmpeg`）。無くても解析・CSVは動作し、動画はmp4vのまま出力されます。

**取得できる指標**：骨盤-肩 分離角(H-B) / 踏み出し脚 膝角=ブロック(H-H) / 体幹前傾(H-B,H-D) / 腕スロット(H-D)

> 1台のスマホ=2D解析のため面外動作には誤差。**同一画角での相対変化・トレンド**で判断してください。撮り方は `../video_capture_guide.md` を参照。


- フロントマターの `type`（daily/throwing/monthly）と日付命名規則に依存します。
- 空欄（未記入）は自動でスキップされるので、埋まっていない項目があっても動きます。
- 列はファイル群のフィールドの和集合。新しい項目を足しても壊れません。
