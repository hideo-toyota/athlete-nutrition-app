# フェーズ3：データ記録システムの設計（data_system_design.md）

- 作成日: 2026-06-16
- 基盤: `project_charter.md` ＋ `analysis_phase1.md` ＋ `hypotheses_priority.md`（v2）
- 環境: Obsidian（**Dataview＋Templater導入済**）、入力はスマホ/PC両方、Garmin連携
- 設計の最優先原則: **1日5-10分以内で完了し、継続できること**。完璧な記録より続く記録。

---

## 0. 設計思想（なぜこの形か）

1. **形式＝Markdown＋YAMLフロントマター**。各ノート冒頭の `--- ... ---` に構造化フィールドを置く。
   - 人間に読みやすく（Obsidianネイティブ）、かつ機械で集計できる（Dataview / `scripts/`のPython）。
   - 「メモ（自由記述）」と「数値（構造化）」を1ファイルに共存させられる。
2. **3層 × 入力頻度を分離**。負担を「毎日は超軽量・投げた日だけ追加・月1でしっかり」に配分。
3. **入力は選択肢/数値中心**。迷いを減らし、スマホでも速い。主観は0-10スケールで統一。
4. **Garminの値は手写し最小限**（睡眠スコア・安静時HR・HRViの3つだけ）。自動連携が要るなら将来拡張。
5. **すべての項目はフェーズ2の仮説に紐づく**（測る理由が明確＝続く）。末尾の対応表参照。

---

## 1. フォルダ構成（Obsidian vault内）

`pitching_analysis/templates/` のテンプレートを Obsidian の「テンプレートフォルダ」にコピーして使う。vault側の推奨構成：

```
野球記録/                      ← vault内の任意の親フォルダ
├── 00_ダッシュボード.md        ← Dataviewで全体を一覧（手入力ゼロ）
├── daily/                     ← 日次ノート（毎日・超軽量）
│   └── 2026-06-16.md
├── throwing/                  ← 投球セッション（投げた日だけ）
│   └── 2026-06-16_bullpen.md
├── monthly/                   ← 月次テスト（月1）
│   └── 2026-06.md
└── _templates/                ← Templater用テンプレ（本リポジトリからコピー）
    ├── tpl_daily.md
    ├── tpl_throwing.md
    └── tpl_monthly.md
```

> 本リポジトリの `templates/` = vaultの `_templates/` に入れる中身。`examples/` = 記入例（コピー不要・参照用）。`scripts/` = 分析用Python（vault外でも可）。

---

## 2. テンプレート①：日次ノート（`tpl_daily.md`）｜目安30秒-2分

毎日の超軽量ログ。Garminを見て3つ写し、主観を0-10で。

**YAMLフィールド辞書**

| フィールド | 型 | 内容 | 由来仮説 |
|---|---|---|---|
| `date` | 日付 | 自動（Templater） | — |
| `type` | 固定 | `daily` | — |
| `weight_kg` | 数値 | 起床時体重 | H-A, H-J |
| `sleep_h` | 数値 | 睡眠時間(Garmin) | H-A, H-J |
| `sleep_score` | 数値 | Garmin睡眠スコア | H-A, H-J |
| `resting_hr` | 数値 | 安静時心拍(Garmin) | H-J(回復), H-A |
| `hrv` | 数値 | HRV(Garmin, 任意) | H-J, H-I |
| `recovery` | 0-10 | 主観的回復感 | H-J |
| `cuff` | 0-10 | 後方カフ違和感（0=無症状） | H-D, H-G |
| `energy` | 0-10 | 気力・元気 | H-A(LEA兆候) |
| `thoracic_drill` | bool | 胸椎モビリティ実施 | H-B |
| `carb_g` | 数値 | 糖質量(実験期のみ・任意) | H-A |
| `train` | タグ/語 | その日のトレ概要(例: 下半身/上半身/ラン/休) | H-I, H-J |
| `notes` | 自由 | 一言メモ | — |

## 3. テンプレート②：投球セッション（`tpl_throwing.md`）｜投げた日だけ・2-4分

壁当て・フラット・ブルペン・登板すべてここ。登板時のみイニング詳細を埋める。

**YAMLフィールド辞書**

| フィールド | 型 | 内容 | 由来仮説 |
|---|---|---|---|
| `date` / `type` | — | 自動 / `throwing` | — |
| `session` | 選択 | `wall`/`flatground`/`longtoss`/`bullpen`/`game` | H-F(ランプ管理) |
| `pitch_count` | 数値 | 総球数 | H-F, H-J |
| `intensity` | % | 体感強度(30/50/75/100) | H-F |
| `velo_max` / `velo_avg` | 数値 | 球速(測定時) | H-C, H-H |
| `cue` | 選択 | `internal`/`external`/`mixed` | H-E |
| `output_feel` | 0-10 | 思い切り投げられた感(出力解放) | H-E, H-G |
| `pain` | 0-10 | 投球中の痛み | H-G, H-D |
| `pain_loc` | 語 | 痛み部位(例: 後方/前方/肘) | H-D |
| `innings` | 数値 | 登板回数(game時) | H-K |
| `pitch_by_inning` | リスト | イニング別球数(game時) | H-K, H-F |
| `strikes` / `walks_hbp` | 数値 | ストライク数・四死球(game時) | H-K |
| `video` | リンク | 動画URL/添付(任意) | H-B, H-H |
| `next_day_cuff` | 0-10 | 翌日カフ違和感(翌日追記) | H-D |
| `recovery_days` | 数値 | 完全回復までの日数(後日追記) | H-J |
| `notes` | 自由 | 感覚・気づき | — |

> **制球効率(H-K)** は `strikes`/`pitch_count`＝ストライク率、`pitch_count`/`innings`＝1イニング球数としてDataview/スクリプトで自動算出。手計算不要。

## 4. テンプレート③：月次テスト（`tpl_monthly.md`）｜月1・15-20分

伝達効率と可動域の客観KPI（フェーズ2の物差し）。これが球速の"なぜ"を説明する。

**YAMLフィールド辞書**

| フィールド | 型 | 内容 | 由来仮説 |
|---|---|---|---|
| `date` / `type` | — | 月初など / `monthly` | — |
| `cmj_cm` | 数値 | 垂直跳び(CMJ) | H-C |
| `rmbtv` | 数値 | 回転系メディシンボール投げ速度 or 距離 | H-C, H-H |
| `velo_max` / `velo_avg` | 数値 | その月の球速 | H-C |
| `ir_throw` / `ir_nonthrow` | 度 | 内旋ROM(投球側/非投球側) | H-D |
| `trm_deficit` | 度 | 全回旋可動域の左右差 | H-D |
| `thoracic_L` / `thoracic_R` | 度 | 胸椎回旋ROM(左右) | H-B |
| `squat_max` / `dl_max` | kg | 任意(出力土台の確認) | H-C |
| `video` | リンク | フォーム動画(分離/前脚/連鎖) | H-B, H-H |
| `notes` | 自由 | 所見・今月の変化 | — |

---

## 5. タグ＆リンク設計

- **タグ**: `#pitching/daily` `#pitching/throwing` `#pitching/monthly`（typeと冗長だがタグ検索/グラフビュー用）。痛みが出た日は `#pitching/pain`、好投は `#pitching/highlight`、不調は `#pitching/issue` を本文に付与（憲法のアドホック分析用）。
- **リンク**: 投球ノートから関連する月次ノート `[[2026-06]]` や仮説検証メモへリンク。動画は `![[...]]` 添付 or 外部URL。
- **命名規則**: daily=`YYYY-MM-DD`、throwing=`YYYY-MM-DD_session`、monthly=`YYYY-MM`。スクリプトとDataviewはこの規則とtypeに依存。

---

## 6. ダッシュボード（`00_ダッシュボード.md`）

Dataviewで手入力ゼロの一覧を生成。`templates/dashboard.md` を参照（直近日次表・直近投球表・球速推移・無痛継続日数・胸椎ドリル継続率・登板の制球効率などを自動集計）。

---

## 7. 運用フロー（続けるための型）

- **毎朝（30秒-2分）**: スマホでTemplaterから日次ノート作成→Garmin3値＋主観を選択→保存。
- **投げた日（+2-4分）**: 投球ノート作成→セッション種別・球数・強度・キュー・痛み・出力感。翌朝に `next_day_cuff` を1つ追記。
- **月1（15-20分）**: 月次テスト（CMJ/RMBTV/ROM/動画）。
- **週次振り返り**: ダッシュボードを眺めるだけ（Dataviewが集計済）。気づきを月次ノートか専用メモに。
- **原則**: 埋まらない項目は空欄でOK。**空欄を許容することが継続の鍵**。

---

## 8. 分析・可視化（`scripts/`）

Dataviewで日々のトレンドは見られるが、相関分析・グラフ・他AIへの共有用に `scripts/` のPythonを用意：
- `extract_to_csv.py`: vaultのMarkdownフロントマターを走査し `daily.csv` / `throwing.csv` / `monthly.csv` を出力。
- `analyze.py`: 主要トレンド（球速・回復・無痛継続・制球効率・胸椎ROM）をグラフ化し、仮説別サマリーを出力。
- 使い方は `scripts/README.md` 参照（依存: Python3＋pyyaml＋pandas＋matplotlib）。

---

## 9. KPI ↔ 仮説 対応表（測る理由）

| KPI | 記録場所 | 検証する仮説 |
|---|---|---|
| 胸椎回旋ROM、動画の分離タイミング | 月次・投球 | H-B(P1) |
| CMJ・RMBTV・球速 | 月次・投球 | H-C(P2), H-H(P7) |
| 球数×強度・セッション種別の推移 | 投球 | H-F(P3) |
| 球数あたりカフ違和感・IR/TRM | 投球・月次 | H-D(P4) |
| キュー種別×出力感×保持(翌日球速/制球) | 投球 | H-E(P5) |
| 無痛継続日数×出力感 | 日次・投球 | H-G(P6) |
| 回復日数×球数強度・HRV/安静時HR | 投球・日次 | H-J(P8) |
| ラン頻度×CMJ/RMBTV/球速 | 日次・月次 | H-I(P9) |
| 1イニング球数・ストライク率・四死球 | 投球(game) | H-K(P10) |
| 体重・睡眠・気力・(糖質) | 日次 | H-A(P11, n=1実験) |

> この対応表があるので、「なぜこれを記録するのか」が常に明確。続かない記録項目は、紐づく仮説ごと見直す。
