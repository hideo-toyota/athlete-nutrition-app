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

# (実装予定) log / score / review … 判断→DCA比で機械採点→較正の閉ループ
```

- 設定は宣言的: [`config.json`](config.json)(コア/サテライト・上限 2.5%/5%/10%・規律しきい値・DCAベンチ)。
- データはファイル: [`portfolio.json`](portfolio.json)、[`indices/`](indices)(指数構成=手入力概算)。
- 生成物は [`outputs/`](outputs)(`honest_mirror.md` / `discipline_check.md`)。

## 設計ドキュメント(これが本体)
- [DESIGN_PRINCIPLES.md](DESIGN_PRINCIPLES.md) — 憲法(背骨+6原則)
- [SPEC.md](SPEC.md) — 契約(データ構造・インターフェイス)
- [PLAN.md](PLAN.md) — 実装計画(mirror→check→log/score→review)
- [WORKFLOW.md](WORKFLOW.md) — 原則→実装のワークフロー(サブエージェント)
- [CLAUDE.md](CLAUDE.md) — オーケストレーター指示(Discord窓口の振る舞い)

## エージェント / スキル(Discord連携の頭脳)
- `.claude/agents/` — 分析チーム(mirror-keeper / data-fetcher / fundamental-analyst / devils-advocate / discipline-auditor / logbook-keeper)+ ビルドチーム。
- `.claude/skills/` — `market-pulse`(米国+日本の市況をWebでリアルタイム取得)、`equity-analysis`(規律ある個別株分析)。

## ⚠️ `spike/` について
`spike/` は**旧プロトタイプ(参照専用)**。`DESIGN_PRINCIPLES` 制定前に書かれ、「買い候補」ラベルを出すなど原則に反します。**判断には使わないでください**([spike/README.md](spike/README.md))。

## 動作確認
```bash
python3 -m py_compile radar/*.py
python3 -m radar mirror
python3 -m radar check buy 7203 100000 Financials
```
