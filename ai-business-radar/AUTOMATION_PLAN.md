# AUTOMATION_PLAN — nightly data refresh and analysis packet

目的は「毎日、取得失敗で全体を止めず、最新データがあれば使い、無ければ stale として正直に表示する」こと。
自動売買・売買推奨・ランキング・価格目標・利益保証はしない。

## 1. 分離するジョブ

### Job A: data-fetch(20:45 JST)

ネットワークあり。research_queue / evidence / LLM handoff は作らない。

- EDINET DB companies: 当日 companies raw を取得する。
- EDINET DB financials: `data/metadata/edinetdb_company_codes_*.txt` の最新ファイルを使い、offset/limit で分割取得する。
- J-Quants watchlist REST: `data/metadata/jquants_watchlist.txt` がある場合だけ `fetch-jquants` で監視銘柄を更新する。現CLIは取得とderived生成が一体なので、これは例外的に `data/derived` を更新するが、research/evidence/LLM packet は作らない。
- J-Quants market-wide Bulk: 現時点では既存 raw を利用する。広域 bulk downloader は正式CLI化するまで LaunchAgent には組み込まない。

失敗時:

- raw を消さない。
- offset は成功時だけ進める。失敗時は同じ offset を次回再試行する。
- stdout/stderr は `outputs/automation/<asof>/` に保存する。
- APIキー値・provider本文は表示しない。

### Job B: build-and-brief(21:30 JST)

ネットワークなし。既存 raw / derived だけを読む。

- `daily-update` を実行し、EDINET/J-Quants derived、research queue、investor brief、LLM handoff packet、Discord用promptを生成する。
- 取得が失敗して当日rawが無い場合でも、`daily-update` の skipped / failed サマリで状態を出す。
- `doctor` も実行し、鮮度差・coverage・空の decision log を確認する。

失敗時:

- 前日以前の data/raw / data/derived を消さない。
- ログを残す。
- 生成できた成果物だけを残す。

### Job C: retry-doctor(06:30 JST)

ネットワークなしが既定。前夜の成果物が無い場合に再生成を試す。

- `doctor` を実行する。
- `outputs/investor_brief/<asof>.md` が無ければ `build-and-brief` を再実行する。
- `RADAR_RETRY_FETCH=1` のときだけ `data-fetch` も再実行する。

### Job D: weekend-heavy(手動または週末)

重い取得・全件棚卸し用。日次ジョブに混ぜない。

- EDINET financials の残 offset を進める。
- J-Quants Bulk downloader の正式CLI化後に market-wide bulk を更新する。
- audit-report の上位 mismatch を原因分解する。

## 2. 標準スケジュール

| 時刻(JST) | ジョブ | 理由 |
|---|---|---|
| 20:45 | data-fetch | J-Quants 日次・EDINET更新を拾いやすく、21:30の分析生成まで余裕を持つ |
| 21:30 | build-and-brief | 夜のDiscord/Claude分析に使う packet を生成 |
| 06:30 | retry-doctor | 前夜失敗・Macスリープ・一時的API失敗の検知と再生成 |
| 週末 | weekend-heavy | API上限を食う処理を日次運用から分離 |

## 3. 失敗に強くするルール

- ネット取得と分析生成を同じジョブにしない。
- fetch失敗時も build-and-brief は既存raw/derivedで走らせる。
- EDINET financials は offset state を成功時だけ進める。
- J-Quants market-wide bulk の正式取得が未整備でも、既存bulk derived と watchlist REST で夜の分析を継続する。
- どのジョブも raw本文・APIキー値・`.env` の中身をログに出さない。
- 実データのログは `outputs/automation/`、状態は `data/metadata/automation/` に置く。どちらも git 追跡しない。

## 4. 手動インストール方針

LaunchAgent はテンプレートだけをコミットする。実登録はMac上で本人が行う。

理由:

- `~/Library/LaunchAgents` はローカル環境差がある。
- APIキー・ローカルraw・Macスリープ設定は本人環境に依存する。
- 自動取得を有効にする前に `scripts/automation/*.sh` を手動実行してログを確認する。

## 5. 完了条件

- `scripts/automation/daily_fetch.sh YYYY-MM-DD` が取得系を独立実行し、失敗してもログを残す。
- `scripts/automation/build_and_brief.sh YYYY-MM-DD` がネットなしで日次packetを生成する。
- `scripts/automation/retry_doctor.sh YYYY-MM-DD` が診断と再生成を行う。
- LaunchAgentテンプレートから 20:45 / 21:30 / 06:30 の自動化を登録できる。

## 6. 次に正式化する未完

- J-Quants Premium Bulk の正式CLI化。現状の広域bulk取得は一時スクリプト由来なので、LaunchAgentにはまだ組み込まない。
- EDINET全件取得の offset 完了率を `doctor` に表示する。
- `outputs/automation/<asof>/summary.json` を生成し、Discordへ「成功/失敗/鮮度」を短く出す。
