# Personal Equity Research Radar

自分の投資判断を「**検証し・規律を保ち・学びを残す**」ための個人用の補助ツール。
**予測はしない。最終判断は人間。** 設計の正は [DESIGN_PRINCIPLES.md](DESIGN_PRINCIPLES.md)(背骨+6原則)。

> ⚠️ 投資助言ではありません。出力の集中度やラベルは整理用で、売買は指示しません。結果の責任は自分にあります。

## これは何か / 何でないか
- **である**: look-through 集中度を映し(自己欺瞞を防ぐ)、売買案を規律でゲートし、判断を記録・検証する道具。
- **でない**: 予測機・自動売買・公開サービス・「勝てる手法」。

## 使い方(本体 = `radar/`)

`ai-business-radar/` ディレクトリで:

```bash
# ① 正直な鏡:look-through の真の集中度(指数の中身まで合算)
python3 -m radar mirror

# ② 規律の番人:売買案を上限/過熱/ナンピンに照らす(買う前に必ず)
python3 -m radar check buy 7203 100000 Financials
python3 -m radar check add NVDA 100000              # 例: 既に上限 → 却下

# ③ 閉ループ:判断を反証可能な形で記録 → 期日にDCA比で機械採点 → 較正
python3 -m radar log       # journal/decision_input.json を追記(予測必須・override理由必須)
python3 -m radar score     # journal/prices.json の horizon終値で採点(未来不参照)
python3 -m radar review    # outputs/journal_review.md(裁量 vs 規律 / 対DCA)

# ④ データ層:APIキー確認 / EDINET DB最小sync / feature生成
python3 -m radar data-check --offline
python3 -m radar data-check --live --provider jquants
python3 -m radar data-check --live --provider edinet-db
python3 -m radar sync --provider edinet-db --dataset companies --asof YYYY-MM-DD --page 1 --per-page 1
python3 -m radar sync --provider edinet-db --dataset financials --code E02144 --years 1 --period annual --asof YYYY-MM-DD
python3 -m radar sync --provider edinet-db --dataset financials --codes-file data/metadata/edinetdb_company_codes_YYYYMMDD.txt --offset 0 --limit 400 --years 1 --period annual --asof YYYY-MM-DD
python3 -m radar build-features --provider edinet-db --dataset financials --raw-path data/raw/edinet-db/financials/<asof>/<file>.json --asof YYYY-MM-DD
python3 -m radar build-company-map --raw-dir data/raw/edinet-db/companies/<asof> --asof YYYY-MM-DD
python3 -m radar build-jquants-features --asof YYYY-MM-DD
python3 -m radar research-queue --asof YYYY-MM-DD
python3 -m radar evidence E02144 --asof YYYY-MM-DD
python3 -m radar llm-brief --asof YYYY-MM-DD
```

判断ログ `decision_log.jsonl` は**追記専用**(decision も outcome も別行・過去は改変しない=後知恵対策)。個人データなので `.gitignore` 済み(テンプレは `journal/*.example.json`)。

- 設定は宣言的: [`config.json`](config.json)(コア/サテライト・上限 2.5%/5%/10%・規律しきい値・DCAベンチ)。
- データはファイル: [`portfolio.json`](portfolio.json)、[`indices/`](indices)(指数構成=手入力概算)。
- 生成物は [`outputs/`](outputs)(`honest_mirror.md` + `honest_mirror.csv` / `discipline_check.md`)。
- 有料データ層は A1 + EDINET DB Phase B minimal sync(companies/financials)まで実装済み。
  J-Quants はユーザー許可済み Premium Bulk raw をローカル取得済みの場合に限り、`build-jquants-features`
  で `data/derived/features/jquants_equity_v1` を生成できる(API sync ではない・ネット/APIキーなし)。
  Claude等LLMへの取得本文投入は `LICENSE_MATRIX.md` の確認対象。
  Phase C minimal feature生成(EDINET DB financials raw → data/derived)、EDINET companies derived map、
  J-Quants Bulk local feature生成、
  derivedだけを読む D0 research_queue/evidence、
  LLM投入用packet生成(`llm-brief`, API呼び出しなし)は実装済み。
  `research-queue` / `evidence` / `llm-brief` は EDINET financials を主入力にし、
  `edinet_company_map_v1` があれば J-Quants `jquants_equity_v1` の株価/出来高/20・60・252営業日リターンを
  補助コンテキストとして含める(売買順・推奨・予測ではない)。
  `daily-update` は EDINET companies raw が同じ asof にあれば `edinet_company_map_v1` も自動生成し、
  EDINET evidence/brief に J-Quants の当時株価コンテキストを結合する。
  provider raw本文の Claude等LLM投入と自動API送信は未実装・`LICENSE_MATRIX.md` の確認対象。

## 使い方プロンプト集
Discordから送る分析指示の例は [PROMPTS.md](PROMPTS.md)。

## 実運用の立ち上げ
ゼロから Discord 連携・実データ投入・日々のループまでの手順は [RUNBOOK.md](RUNBOOK.md)。

## 設計ドキュメント(これが本体)
- [DESIGN_PRINCIPLES.md](DESIGN_PRINCIPLES.md) — 憲法(背骨+6原則)
- [SPEC.md](SPEC.md) — 契約(データ構造・インターフェイス)
- [PLAN.md](PLAN.md) — 実装計画(mirror→check→log/score→review)
- [FEATURE_PHASE_C_SPEC.md](FEATURE_PHASE_C_SPEC.md) — EDINET DB financials feature生成の契約
- [FEATURE_PHASE_C_PLAN.md](FEATURE_PHASE_C_PLAN.md) — Phase C 実装順序と受け入れ基準
- [WORKFLOW.md](WORKFLOW.md) — 原則→実装のワークフロー(サブエージェント)
- [CLAUDE.md](CLAUDE.md) — オーケストレーター指示(Discord窓口の振る舞い)
- [DALOOPA_LANE_SPEC.md](DALOOPA_LANE_SPEC.md) — Daloopa外部分析レーン(本体data層とは隔離)

## エージェント / スキル(Discord連携の頭脳)
- `.claude/agents/` — 分析チーム(mirror-keeper / data-fetcher / fundamental-analyst / devils-advocate / discipline-auditor / logbook-keeper)+ ビルドチーム。
- `.claude/skills/` — `market-pulse`(米国+日本の市況をWebでリアルタイム取得)、`equity-analysis`(規律ある個別株分析)。
- Daloopaは外部分析補助として別レーン。OAuth/setup確認までは analysis/DCF/tearsheet を走らせず、`ai-business-radar` の `data/*` や `research_queue` には混ぜない。

## ⚠️ `spike/` について
`spike/` は**旧プロトタイプ(参照専用)**。`DESIGN_PRINCIPLES` 制定前に書かれ、「買い候補」ラベルを出すなど原則に反します。**判断には使わないでください**([spike/README.md](spike/README.md))。

## 動作確認
```bash
python3 -m py_compile radar/*.py
python3 -m radar mirror
python3 -m radar check buy 7203 100000 Financials
```
