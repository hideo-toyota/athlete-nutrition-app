# pitching_analysis — 投球復帰・コンディショニング長期検証

37歳右投手の復帰過程とコンディショニング戦略を、**データ蓄積 → 仮説検証 → 戦略更新**のサイクルで支える検証プロジェクト。Claude Code が検証パートナーとして分析・設計を担う。

## このフォルダの構成

| パス | 内容 |
|---|---|
| `project_charter.md` | 本プロジェクトの「憲法」。文脈・原則・仮説・依頼・制約を集約。新セッションはここから開始。 |
| `analysis_phase1.md` | （フェーズ1）批判的分析と盲点の発見 — **作成済（6本のリサーチで根拠付け）** |
| `hypotheses_priority.md` | （フェーズ2）仮説の整理と優先順位付け — **作成済v2（13仮説・確信度軸を追加して再スコア）** |
| `data_system_design.md` | （フェーズ3）データ記録システム設計書 — **作成済** |
| `templates/` | Obsidian用テンプレート（日次/投球/月次/ダッシュボード） — **作成済** |
| `examples/` | 記入例（日次・投球・登板・月次） — **作成済** |
| `scripts/` | CSV抽出・可視化＋動画姿勢解析(video_pose.py) — **作成済** |
| `video_capture_guide.md` | フォーム動画/キーフレームの撮影ガイド＋チェック表 — **作成済** |

## 進行状況（2026-06-16 時点）

- [x] 憲法（charter）保存・環境制約の合意（保存先＝本リポジトリ内 `pitching_analysis/`）
- [x] 追加データ収集（身長体重/投球量/筋トレ実態/痛み/睡眠/栄養/Garmin睡眠）
- [x] **フェーズ1: 批判的分析**（`analysis_phase1.md`／5本＋心理1本の並列リサーチで根拠付け）← *あなたの検証待ち*
- [x] **フェーズ2: 仮説の優先順位付け**（`hypotheses_priority.md`／13仮説・確信度軸つきv2）
- [x] **フェーズ3: データ記録システム設計**（`data_system_design.md`＋テンプレ＋記入例＋スクリプト）← *運用開始準備OK*

## 次の一歩（運用開始）
1. `templates/` を Obsidian の `_templates/` にコピー（Templater用）。`templates/dashboard.md` を vault 直下に `00_ダッシュボード.md` として配置（Dataview）。
2. まず **月次テスト**でベースライン取得（CMJ・RMBTV・ROM・球速・動画＝H-Cの物差し）。
3. **日次ノート**を毎朝30秒〜2分、**胸椎ドリル**を日課に（H-B）。投げた日は**投球ノート**。
4. 必要に応じ `scripts/` で CSV 抽出・グラフ化（`examples/` で動作確認済み）。

## 独立リポジトリへの切り出し（将来）

このフォルダは自己完結設計。独立させたくなったら次のいずれか:

```bash
# 方法1: 履歴ごと切り出す
git subtree split -P pitching_analysis -b pitching-only
# 新リポジトリを作成・追加後
git push <new-repo> pitching-only:main

# 方法2: 単純コピー（履歴不要なら）
cp -r pitching_analysis /path/to/new-repo/
```

## Obsidian への取り込み

本リポジトリを `git pull` するか、`pitching_analysis/` をコピーして Obsidian vault に配置する。テンプレート・タグ設計はフェーズ3で確定。
