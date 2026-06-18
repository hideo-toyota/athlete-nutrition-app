# DATASET_SCOPE — Phase B(sync)で最初に取り込む dataset の選定(実装前)

> 正は DATA_LAYER_SPEC.md / LICENSE_MATRIX.md / DESIGN_PRINCIPLES.md / CLAIMS.md / CLAUDE.md。
> 目的: Phase B(sync)を**いきなり広げない**。「1 provider / 1 dataset / 最小取得単位」で
> sync の配管(raw保存 + provenance + hash + PIT)を低リスクに検証するための **最初の1 dataset** を決める。
> ⚠️ 本書は設計判断のみ。実 API は叩かない・raw 保存しない・実装しない。

## 0. 選定の前提(なぜ「軽い参照系」から始めるか)
- Phase B の狙いは「巨大な財務データを集めること」ではなく **sync の骨格(取得→raw保存→provenance→
  hash→PIT→manifest)が壊れず再現することの検証**。だから**被害範囲が小さく・静的で・PIT が単純で・
  Phase C(feature)の土台になる参照系(マスタ)**から始めるのが安全(原則3・6)。
- 市場データ(prices)・財務(financials)・比率(ratios)は**価値は高いが、PIT(available_at の引け後判定)・
  欠損・大きさ・改訂版管理が重い**。最初の1本には不向き。

## 1. 候補比較(◎=良い / ○ / △ / ✕=不適 or ブロッカー)

| dataset | ToS/LICENSE 未確認リスク | raw保存の要否 | available_at/asof | provenance/hash | LLM非投入の守りやすさ | Phase C 接続 | 日本株個人価値 | 実装の小ささ | 失敗時の被害 |
|---|---|---|---|---|---|---|---|---|---|
| **EDINET DB companies** | △ raw一時キャッシュ=条件付き可・再配布禁止=確認済 / retention日数=未確認 | ○ マスタ=軽量・更新少 | ◎ ほぼ静的=retrieved_at | ◎ JSON・小 | ◎ 保存のみ・LLM不要 | ◎ entity master(edinet_code) | ◎ 財務分析の名寄せ土台 | ◎ per_page=1〜数件 | ◎ 機微なし・静的 |
| J-Quants listed-info | ✕ raw保存=未確認(致命) | ○ マスタ=軽量 | ◎ 静的=retrieved_at | ◎ | ◎ | ◎ entity master(securities_code) | ◎ サテライト universe 土台 | ◎ | ◎ |
| J-Quants prices | ✕ raw保存=未確認(致命) | ◎ 必須(時系列) | △ 引け後・取引日判定が重い | ○ | ◎ | ○ | ○ | △ 量が多い | △ |
| J-Quants financials | ✕ raw保存=未確認(致命) | ◎ 必須 | △ disclosure_date・改訂版 | ○ | ◎ | ◎ | ◎ | △ | △ |
| J-Quants earnings-calendar | ✕ raw保存=未確認(致命) | ○ | △ 予定→確報の版管理 | ○ | ◎ | ○(value-audit のサイクル境界) | ○ | ○ | ○ |
| EDINET DB financials | △ 一時キャッシュ可だが retention 未確認 | ◎ 必須 | △ disclosure/submit | ○ | ◎ | ◎(本命) | ◎ | △ | △ |
| EDINET DB ratios | △ 同上 + **分析スコアは Cabocia 著作物=INFERENCE固定** | ◎ | △ 元financials継承 | ○ | ◎ | ○ | ○ | △ | △(誤FACT化リスク) |
| Daloopa(米国株) | ✕ **別レーン**(DALOOPA_LANE_SPEC)。Phase B 対象外 | — | — | — | △(MCP=LLM投入前提) | ✕ data層に混ぜない | △ 米国偏重・目的ズレ | — | — |

## 2. 結論:最初の1 dataset = **EDINET DB `companies`(企業マスタ)**

**理由(忖度なし)**:
1. **ToS のブロッカーが一番浅い**。J-Quants 系は **raw保存(J2)が未確認=致命**で、sync(=raw保存)は
   原理的に踏み出せない。EDINET DB は **一時キャッシュ=条件付き可・再配布禁止=確認済**(LICENSE_MATRIX)。
   残るのは **retention 日数(E3)** の確定だけ。→ 最短で安全に GO 条件を満たせる。
2. **参照系マスタ**なので available_at がほぼ静的(retrieved_at)で、**PIT の最難所(引け後判定・改訂版)を
   回避**しつつ sync 配管を検証できる。
3. **被害範囲が最小**(静的・小さい・機微情報なし・売買に直結しない)。
4. **Phase C の土台**(edinet_code↔securities_code の entity mapping の起点)になり、無駄にならない。

> EDINET DB 側は本人確認済みの個人内 raw 一時キャッシュ前提で GO。J-Quants 側は raw保存/retention が未確認の間 NO-GO。
> user の暫定案(「listed-info か companies のような軽い参照系から」)は**方向性として妥当**。
> 2択のうち **companies を推す**のは、J-Quants の raw保存が未確認(致命)で listed-info はまだ sync できないため。
> J-Quants 側は **J2/J3 が確認でき次第、listed-info を“2本目”** にするのが自然。

## 3. 実装に進むための LICENSE_MATRIX 確認セル(本人)
**EDINET DB `companies` / `financials` を sync する最小条件**:
- [x] **E2**(raw ローカルキャッシュ可否):本人が個人内 raw 一時キャッシュの許容を確認済み。
- [x] **E3**(retention / purge):当面は手動 purge + 定期再取得で運用。大規模反復前に TTL/purge を追加検討。
- [x] **E7**(再配布禁止):個人内利用に留め、再配布しない前提を維持。
- [ ] **E9**(attribution):公開しない前提を維持(公開に切り替える場合のみ再確認)。
- （第三者LLM入力 **E5** は Phase B では**不要**=sync は LLM に渡さない。B では触れない。)

**J-Quants 系(listed-info 以降=2本目)に進む条件**:
- [ ] **J2**(raw保存)/ **J3**(retention)を原本で確認(現状 未確認=致命のため NO-GO)。

## 4. 非対象(今回広げない)
- prices / ratios / earnings-calendar（PIT・量・改訂が重い。financials の配管検証後）。
- Daloopa（別レーン・DALOOPA_LANE_SPEC。data 層へ混ぜない)。
- feature 生成 / research_queue / evidence / LLM 投入(Phase C/D・本書の範囲外)。

> ※本書は投資助言ではない。データ取得の安全な最小スコープを定義する設計判断である。
