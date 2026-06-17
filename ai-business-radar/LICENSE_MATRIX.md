# LICENSE_MATRIX — データ提供元の利用条件(v3・要・本人確認)

> ⚠️ 雛形。各セルは**規約原本を読んで**出典URL+確認日付きで埋める。確認できないセルは「未確認」と書く
> (CLAIMS.md:出典なきToSを FACT 扱いしない)。**raw保存・LLM入力・再配布が許容と確認できるまで sync は NO-GO**(D1)。

## 提供元(検証済みFACT, as_of 2026-06-14 Web)
- **EDINET DB**(運営 Cabocia株式会社)。**両ドメインとも公式**:
  - REST API: `https://edinetdb.com/v1/`(12エンドポイント:企業検索/財務/比率/分析スコア/ランキング/業種 等)
  - MCP: `https://edinetdb.jp/mcp`(Streamable HTTP)/ 日本語docs `edinetdb.jp/docs/mcp-guide`
  - FSA EDINET の有報を日次同期、JP GAAP/IFRS/US GAAP を正規化。**無料 100/日・Pro 1,000/日(Codex確認・要本人最終確認)**。
  - **canonical/allowed domains**: REST=`edinetdb.com/v1`(開発者ページ例に `edinetdb.jp/v1` もあり=許可ドメインとして明記)/ MCP=`edinetdb.jp/mcp`。規約=`edinetdb.com/legal/terms`。
- **J-Quants**(JPX)。有料契約済(本人)。**ToS本文は未取得=未確認**。

## マトリクス(各セル: 値 / 出典URL / 確認日。不明は「未確認」)

| 項目 | J-Quants(有料) | EDINET DB |
|---|---|---|
| provider / 運営 | JPX | Cabocia株式会社 |
| domain | api.jquants.com 等(要確認) | REST=`edinetdb.com` / MCP=`edinetdb.jp`(両公式) |
| plan(本人契約) | **未確認**(プラン名) | **未確認**(契約プラン・上限。無料=100/日。Pro上限は原本要確認) |
| 規約URL | **未確認**(要記入) | `edinetdb.com/legal/terms`(要・原本確認) |
| 確認日 | 未記入 | 未記入 |
| APIプログラム利用 | 未確認 | 可(REST/MCP提供)※原本で最終確認 |
| raw ローカルキャッシュ可否 | **未確認(致命)** | **未確認**(「一時キャッシュ」許容の見込み・保存期間は別途) |
| 保存期間 / retention / purge義務 | 未確認 | 未確認 |
| 派生特徴量生成 | 未確認 | 加工・分析利用は可の見込み(※AI所見/スコア=Cabocia著作物は別扱い)※原本確認 |
| **LLM/AI入力(分割)** | | |
| └ 第三者LLM(Claude等)へ入力 | **未確認(致命)** | **未確認** |
| └ AI提供側の保持/学習 | 未確認(Anthropic等のデータ方針も別途) | 未確認 |
| └ MCP(edinetdb.jp/mcp)利用 | 該当なし | 可の見込み ※原本確認 |
| └ 送信粒度(raw / derived / 要約のみ) | 未確認(粒度別に可否確認) | 未確認(粒度別に可否確認) |
| 再配布(一括/wrapper API) | 未確認(通常禁止想定) | 一括再配布・wrapper API は禁止の見込み ※原本確認 |
| 社外 / 公開利用 | 未確認 | 商用可の記述あり・**公開時 attribution 要請**(個人内利用と分けて管理) |
| rate limit | 未確認 | 無料100/日・Pro 1,000/日(Codex確認・要本人最終確認) |
| attribution / source表記 | 未確認 | 公開サービスで要請 ※原本確認 |
| 禁止事項 | 未確認 | スクレイピング禁止(API/MCPのみ)・AI所見の不正確性リスク明記 |
| 未確認事項(列挙) | ToS全般 | 規約原本テキスト(保存期間・再配布・LLM入力) |
| 実装上のガード(必須/任意) | (必須: raw git除外・redact 等) | (必須: docID で FSA EDINET 原本遡及・公開時attribution・AI所見をINFERENCE固定) |

## claim-audit(FACT / 未確認 の切り分け, as_of 2026-06-14)
**FACT(検証可)**: 両ドメインとも公式(REST=.com/v1, MCP=.jp/mcp, 運営=Cabocia)。商用可・公開時 attribution・無料100/日・JP GAAP/IFRS/US GAAP正規化。AI所見の誤り可能性を規約/サイトが明記。
**未確認(FACT扱い禁止)**: 規約原本テキスト(raw保存・retention・再配布・**第三者LLM入力**)、本人契約プラン名・Pro上限、J-Quants 有料 ToS 全般、FSA EDINET の具体ライセンス版(Public Data License 1.0 か否か)。
**前回の誤りを訂正**: `edinetdb.jp` は**公式(MCP/日本語docs/規約の日本語面)**。前回の「`.jp`疑義・不採用」は**撤回**。行番号引用(L99-125等)だけは再現不能のため不採用、URL+節名で参照する。
**原本遡及先**: FSA EDINET(`disclosure2dl.edinet-fsa.go.jp`)実在=FACT。

## 判定ゲート
- **致命**: J-Quants/EDINET DB とも「raw保存」「**第三者LLM入力**」「再配布」が**許容と確認できるまで sync は NO-GO**。
- 「第三者LLM入力」は特に注意:取得データを Claude 等に渡すこと自体が再配布/第三者提供に当たらないか、両ToS+AI提供側方針の双方で確認。
- 個人→公開に切り替える場合:attribution 必須化・再配布禁止を再点検(停止条件)。

Sources(検証):
- https://edinetdb.com/ , https://edinetdb.com/developers , https://edinetdb.com/docs/api , https://edinetdb.com/legal/terms , https://edinetdb.jp/docs/mcp-guide
- https://disclosure2dl.edinet-fsa.go.jp/
- ※ `edinetdb.com/legal/terms` の各条文(商用可・一時キャッシュ・一括再配布禁止・wrapper API禁止・公開時attribution・AI所見の不正確性)は **本人が原本で最終確認**して各セルに転記すること。

---

## 本人記入用 ToS 転記ワークシート(空欄・FACTはあなたが原本から埋める)

> 使い方:各設問を**規約原本の該当箇所**で確認し、`回答`/`出典URL`/`確認日`/`原文の要点(引用)` を埋める。
> **確認できない設問は「未確認」と書く**(空欄=未着手と区別)。私(AI)は値を埋めない・キーには触れない。
> 埋め終わったら、下の「## 解除ゲート(段階)」の条件に従って GO/NO-GO が自動的に決まる。

### A. J-Quants(JPX・有料契約)
原本: 利用規約 URL =(未記入) / 契約プラン名 =(未記入)

| # | 設問(Yes/No/条件) | 回答 | 出典URL+節 | 確認日 | 原文の要点 |
|---|---|---|---|---|---|
| J1 | API のプログラム的利用は許可されているか | (未記入) | (未記入) | (未記入) | (未記入) |
| J2 | 取得データを**ローカルに保存(raw キャッシュ)**してよいか(=sync の前提) | (未記入) | | | |
| J3 | 保存の**保持期間/purge 義務**はあるか(あれば期間) | (未記入) | | | |
| J4 | 取得データから**派生指標(比率・成長率等)を生成・保存**してよいか | (未記入) | | | |
| J5 | 取得データを**第三者(Claude等のLLM)に入力**してよいか【致命】 | (未記入) | | | |
| J6 | 上記が条件付き可なら、**送信粒度**(raw不可/要約のみ可 等)の条件は | (未記入) | | | |
| J7 | **再配布**(生データ/wrapper API/一括配布)は禁止か | (未記入) | | | |
| J8 | **レート上限**(1日/1分あたり)・課金区分 | (未記入) | | | |
| J9 | **出典表記(attribution)**の要否(個人内利用/公開時) | (未記入) | | | |
| J10 | その他の**禁止事項**(スクレイピング・自動売買連携 等) | (未記入) | | | |

### B. EDINET DB(Cabocia・REST=edinetdb.com/v1 / MCP=edinetdb.jp/mcp)
原本: 規約 URL = `edinetdb.com/legal/terms`(原本で要確認) / 契約プラン =(未記入・無料100 or Pro1000)

| # | 設問(Yes/No/条件) | 回答 | 出典URL+節 | 確認日 | 原文の要点 |
|---|---|---|---|---|---|
| E1 | API/MCP のプログラム的利用は許可されているか | (未記入) | (未記入) | (未記入) | (未記入) |
| E2 | 取得データを**ローカルに保存(raw キャッシュ)**してよいか・「一時キャッシュ」の定義/期間 | (未記入) | | | |
| E3 | **保持期間/purge 義務** | (未記入) | | | |
| E4 | **派生指標の生成・保存**は可か(※AI所見/分析スコア=Cabocia著作物は別扱い) | (未記入) | | | |
| E5 | 取得データを**第三者LLM(Claude/MCP経由含む)に入力**してよいか【致命】 | (未記入) | | | |
| E6 | 送信粒度の条件(raw/要約) | (未記入) | | | |
| E7 | **再配布**(一括/wrapper API)は禁止か | (未記入) | | | |
| E8 | **契約プランの上限**(Pro=1,000/日 で合っているか)・課金 | (未記入) | | | |
| E9 | **attribution**(公開時の出典表記要請)の具体文言 | (未記入) | | | |
| E10 | AI所見/分析スコアの利用条件(=INFERENCE固定・FACT化禁止は実装側で担保済) | (未記入) | | | |

### 解除ゲート(段階・上のワークシートが埋まると自動的に決まる)
> いまは全ゲート **NO-GO**(未確認のため)。下の条件が「可」で揃った段階だけ解除する。

1. **A1(疎通のみ・raw保存しない・LLMに渡さない)** ← 解除条件: **J1 と E1 が「可」**。
   - キー存在確認 + 最小リクエストで疎通可否を返すだけ。raw を保存せず、取得本文を Claude にも渡さない。
2. **B(sync=raw保存)** ← 追加で **J2/J3 と E2/E3 が「可」**(保持/purge 条件を実装に反映)。
3. **第三者LLM入力(evidence/research を Claude が読む・MCP利用)** ← 追加で **J5 と E5 が「可」**【最重要】。
   - これが「不可/未確認」の間は、**取得データを分析エージェントに渡さない**(value-audit Phase B/C もここに依存)。
4. **公開・配布しない前提の維持** ← **J7/E7 が「再配布禁止」**を確認し、個人内利用に留める(attribution J9/E9 はメモ)。

> 補足: **A1 を通すだけなら J1/E1 の確認で足りる**が、実際の分析(財務を Claude に読ませる)には J5/E5(第三者LLM入力)が必須。
> ここが本丸なので、**J5 と E5 を最優先で確認**することを勧める。
