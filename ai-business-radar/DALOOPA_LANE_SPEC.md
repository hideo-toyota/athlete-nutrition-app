# DALOOPA_LANE_SPEC — Daloopa 外部分析レーンの契約

> Daloopa は `J-Quants / EDINET DB` の data layer とは**別レーン**として扱う。
> この文書は、Daloopa MCP を使う場合に `ai-business-radar` の原則・ToSゲート・規律を壊さないための停止条件を定義する。

## 0. 現在地
- Daloopa plugin はローカルに存在し、`~/.codex/config.toml` 上で enabled。
- Daloopa MCP endpoint は `401 Unauthorized` を返し、OAuth protected resource として応答する。
- 2026-06-18時点では、このセッションで Daloopa tools (`discover_companies` 等) は未露出。
- OAuth / browser approval は未完了。**setup確認より先へ進まない**。

## 1. 目的 / 非目的
- **目的**: 米国保有株などの外部分析補助として、Daloopa の cited financial data を参照する。
- **非目的**: `ai-business-radar` の provider data layer へ即統合すること / raw保存 / research_queue 生成 / 買い候補抽出 / DCFで売買判断すること。
- Daloopa 出力は投資助言ではない。売買は `mirror -> check -> human -> log` の既存フローに従う。

## 2. 絶対ルール
- Daloopa response body / raw data を `data/raw`, `data/cache`, `data/derived` に保存しない。
- Daloopa output を `research_queue`, `evidence`, `value-audit`, `target-check` に混ぜない。
- Daloopa由来の数値は、citation と as_of がない限り FACT 扱いしない。
- ベンダー計算・要約・スコア・モデル出力は `INFERENCE` または `ASSUMPTION` として扱う。
- `tearsheet`, `DCF`, `earnings review`, `comps` は setup成功後も段階的に許可する。初回は実行しない。
- 買い推奨、売買指示、ランキング、期待リターン順の出力は禁止。

## 3. OAuth / setup ゲート
次の順でのみ進む。

1. `codex mcp login daloopa` で公式OAuthを開始。
2. ブラウザURLが `https://mcp.daloopa.com/authorize...` であることを確認。
3. 人間がログイン/許可を完了する。AIは認証情報・token・authファイルを読まない。
4. 新セッションまたはreload後、Daloopa tools の露出を確認:
   - `discover_companies`
   - `discover_company_series`
   - `get_company_fundamentals`
   - `search_documents`
   - `get_stock_prices`
5. tools が見えた場合のみ、`discover_companies("AAPL")` を connectivity probe として1回実行。
6. 返してよいのは `tools visible`, `auth state`, `AAPL probe success/failure`, `company_id`, `latest_available_quarter` まで。

## 4. 段階判定
| phase | allowed | blocked |
|---|---|---|
| D0: plugin presence | plugin / config / MCP endpoint の存在確認 | OAuth token の閲覧 |
| D1: auth setup | 公式OAuth、tools露出確認、AAPL lookup | report生成、raw保存、投資分析 |
| D2: external note | 保有株の決算点検メモ(引用必須・助言なし) | `ai-business-radar` data層統合 |
| D3: integration design | LICENSE / provenance / retention / citation policy の紙設計 | CLI実装、research_queue投入 |

## 5. `ai-business-radar` 統合前の確認事項
Daloopaを第三データ源として統合する前に、最低限以下を確認する。

- Daloopa ToS: MCP/LLM消費の許可範囲。
- raw保存可否、retention、purge条件。
- citation link の利用条件、再配布可否、公開レポートでの attribution。
- Daloopa由来の vendor-calculated metrics を FACT にしない分類ルール。
- cost / quota / rate limit。
- 米国株中心データが、日本中小型を主対象とする本システムの目的を逸らさないこと。

## 6. 最初の実用範囲
setup後に進める場合も、最初は米国保有株の「仮説点検」に限定する。

- 許可候補: `NVDA` / `TSLA` など既存保有の決算メモ。
- 禁止: 新規銘柄探索、買い候補リスト、DCFによる売買判断、ランキング。
- 出力は「分かったこと / 分からないこと / 仮説への影響 / 反証条件 / citation」に限定する。

## 7. GO / NO-GO
- Daloopa OAuth setup: **GO**。
- `discover_companies("AAPL")` probe: **GO after auth**。
- Daloopa実データ分析: **条件付きGO**(D1成功後、外部メモ限定)。
- `ai-business-radar`統合: **NO-GO**(本SPECと別途 LICENSE_MATRIX 追記・監査が完了するまで)。
