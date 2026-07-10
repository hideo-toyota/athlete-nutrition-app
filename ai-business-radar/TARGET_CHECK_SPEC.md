# TARGET_CHECK_SPEC — 「10x Feasibility & Ruin Guard」契約(設計のみ・実装前)

> 設計のみ。コードはこの契約の帰結。正は DESIGN_PRINCIPLES.md / SPEC.md / CLAIMS.md / CLAUDE.md。
> これは **目標倍率の“可視化・監査”ツール**。**銘柄を探さない・推奨しない・予測しない**。

## 0. 目的 / 非目的
- **目的**: 目標倍率(例 10x)に対し、**必要年率・税引後の必要倍率・混合の到達可能性・破綻ライン**を可視化する。
- **非目的(禁止)**: 銘柄入力 / 買い候補 / 銘柄ランキング / 期待リターン順 / 「達成可能・不能」の断定 / 相場や個別株の上昇予測。
- **結論の出し方**: 「達成可能/不能」ではなく **「必要条件」と「破綻条件」** を列挙する。

## 1. 既存原則との関係 / 非回帰
- 純計算・**ネット/API/外部データ/ToS 不要**(データ層とは独立)。
- 主張は CLAIMS 分類(必要年率=CALCULATION、指数の歴史的リターン=参考/ASSUMPTION・FACT扱いしない、目標可否=INFERENCE)。UNSAFE禁止。
- `--asof` で時点固定=再現可能(mirror/score と同実装)。
- 純加法的:既存 `mirror/check/log/score/review` の CLI/I/O/挙動は不変。

## 2. 入力(銘柄は受け取らない)
- `target_multiple`(例 10)/ `horizon_years`(例 5/7/10)
- `current_assets_jpy`(既定: `portfolio.json` 総額)
- `monthly_contribution_jpy`(DCA・任意。既定0)
- 口座区分:`nisa_jpy` / `taxable_jpy`(または比率)→ 税の当て方
- `core_satellite`(既定: `config.json`)、`max_pct_per_name/sector/total`(同)
- `max_drawdown_tolerance_pct`(任意)/ `leverage`(既定1.0=無)/ `emergency_fund_separated`(bool)
- **拒否**: ticker らしき入力・銘柄リスト(渡されたら「この道具は銘柄を扱わない」と停止)。

## 3. 計算式(すべて明示・CALCULATION)
- `required_cagr = target_multiple**(1/horizon_years) - 1`(検証: 10x→5y 58.5% / 7y 38.9% / 10y 25.9%)
- **税引後**(課税分のみ、`t=0.20315`): 税引後 M 倍に必要な税前倍率 `G = 1 + (M-1)/(1-t)`(10x→約12.3x)。**NISA分は `G=M`(非課税)**。口座比率で加重。
- **DCA分解**: 目標額 `W = target_multiple * current`。`current*(1+r)^N + Σ 月次積立の将来価値 = W` を満たす `r` を数値解。**「入金込みの必要r」と「現資産だけの必要r」を併記**(入金が効くほど必要rは下がる=正直に)。
- **混合の到達可能性(中核)**: `total = core_w*core_ret + sat_w*sat_ret`。現在の core/sat 比と上限で、**sat が極端(例10x/20x)でも total が目標に届くか**を表示。例:0.9コア+10%sat=10xでも total≈1.9x → **「10%枠では原理的に10x不可」**。
- **破綻ライン**: 最大損失=Σ(個別株サイズ)。`near_ruin_%`=集中度から算出。**レバレッジ `L` 使用時、約 `1/L` の下落で資本毀損**(例 L=2→-50%で全損)を明示。

## 4. 出力契約(`outputs/target_check.md`)
1. **先頭に不確実性**: 「リターンは予測不能・以下は仮定下の算術」(原則3)。
2. **必要CAGR(税前)** と **税引後の必要倍率/CAGR**(口座区分反映)。
3. **DCA込み vs 現資産だけ** の必要リターン。
4. **★混合の現実**(到達不能性)— 中核として目立たせる。
5. **Ruin**: 最大損失 / 最大DD許容 / near-ruin% / レバレッジ破綻ライン / 生活防衛資金の分離有無。
6. **ギャップ**: 「分散インデックスの**歴史的レンジ(参考・予測でない)**で届く/届かない」。指数リターンは ASSUMPTION/参考と明記。
7. **結論=必要条件リスト + 破綻条件リスト**(達成可能/不能の断定はしない)。
8. **規律との両立所見**: 「この目標は『余剰資金・現物・分散・上限』と両立するか」。
9. 免責:投資助言でない・予測でない・売買指示でない。

## 5. 禁止(構造的ガード)
銘柄入力 / `buy_candidate`・推奨語 / ランキング / 期待リターン順 / 「達成可能・不能」断定 / 相場・個別株の上昇予測(UNSAFE) / 指数が将来 X% と断定。

## 6. CLI
```
target-check --multiple 10 --years 10 [--monthly 250000] [--asof YYYY-MM-DD]
```
- 現資産・core/sat は `portfolio.json`/`config.json` から既定取得。出力 `outputs/target_check.md`。
- 既存5コマンドは不変(追加のみ)。

## 7. テスト(オフライン)
required_cagr(5/7/10y の既知値)/ 税引後倍率(12.3x)/ NISA非課税分岐 / DCA数値解 / **混合の到達不能性**(0.9+10%×10x≒1.9x)/ レバ破綻ライン(L=2→-50%)/ **出力に買い候補語・ランキング・予測が無い** / 銘柄入力の拒否 / 端値(multiple≤1, years≤0, nan/inf)/ 既存非回帰。

## 8. Phase
純計算・ネット無し → **今すぐ実装可能**(データ層のToSブロックと独立)。
