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

## 本人記入用 ToS 転記ワークシート(AI下書き・本人FACT化待ち)

> 使い方:各設問を**規約原本の該当箇所**で確認し、`回答`/`出典URL`/`確認日`/`原文の要点(引用)` を埋める。
> **確認できない設問は「未確認」と書く**(空欄=未着手と区別)。この節は公開ページを読んだAI下書きであり、
> 本人が原本で最終確認するまでFACT化しない。APIキー/.env/データAPIには触れていない。
> 埋め終わったら、下の「## 解除ゲート(段階)」の条件に従って GO/NO-GO が自動的に決まる。

### A. J-Quants(JPX・有料契約)
原本: 利用規約 URL = **未確認**(公開Helpは確認。ログイン後ToS本文は本人確認待ち) / 契約プラン名 = **未確認**(本人確認待ち)

| # | 設問(Yes/No/条件) | 回答 | 出典URL+節 | 確認日 | 原文の要点 |
|---|---|---|---|---|---|
| J1 | API のプログラム的利用は許可されているか | 条件付きYes(個人の私的利用範囲) | <https://jpx-jquants.com/ja> — APIコード例/MCP; <https://jpx-jquants.com/ja/help/usage> — 利用目的・ライセンス | (本人確認待ち) | 公式ページにAPIコード例、MCP/CSV利用の説明あり。HelpはJ-Quants APIを「個人の方の私的利用に限定したサービス」と説明。 |
| J2 | 取得データを**ローカルに保存(raw キャッシュ)**してよいか(=sync の前提) | 未確認(根拠不足。契約中の個人内ローカル保存は明示なし) | <https://jpx-jquants.com/ja/help/usage> — 利用目的・ライセンス | (本人確認待ち) | 自身の投資分析/ポートフォリオ管理は私的利用とされるが、rawキャッシュ保存の明示条件は公開Helpからは特定できない。解約/退会・上位プラン変更後は取得済みデータ削除の記述あり。 |
| J3 | 保存の**保持期間/purge 義務**はあるか(あれば期間) | 条件あり(解約/退会・上位→下位プラン変更時は削除)。契約中retentionは未確認 | <https://jpx-jquants.com/ja/help/usage> — サブスクリプションのキャンセルまたは退会後 / プラン変更後 | (本人確認待ち) | J-Quants APIはデータ販売ではなくデータ利用サービス。解約/退会後は取得済みデータ削除、上位プランで取得したデータはプラン変更後に削除、と説明。 |
| J4 | 取得データから**派生指標(比率・成長率等)を生成・保存**してよいか | 条件付きYes(個人の投資分析・ポートフォリオ管理の範囲。継続反復の第三者提供は不可) | <https://jpx-jquants.com/ja/help/usage> — 私的利用とは / ブログやインターネット記事 | (本人確認待ち) | 私的利用は自身の投資分析/ポートフォリオ管理。分析結果/手法の公開は可。ただし投資分析結果を継続反復して第三者へ提供/配信する行為は私的利用ではない。 |
| J5 | 取得データを**第三者(Claude等のLLM)に入力**してよいか【致命】 | 未確認かつ高リスク。第三者が閲覧できる状態になるなら私的利用外の可能性が高い | <https://jpx-jquants.com/ja/help/usage> — 私的利用とは / アプリ公開・配布 | (本人確認待ち) | Helpは「本データを第三者が閲覧できる状態」は私的利用ではない、アプリ運営者サーバにJ-Quants由来データが蓄積・中継される構成は禁止、と説明。Claude等第三者LLMへのraw投入、AI側保持/学習、MCP経由送信の可否は明示なし。 |
| J6 | 上記が条件付き可なら、**送信粒度**(raw不可/要約のみ可 等)の条件は | 未確認。ただしrawを閲覧可能な形で第三者へ出すことは不可 | <https://jpx-jquants.com/ja/help/usage> — ブログやインターネット記事 / 取得データの分析結果 | (本人確認待ち) | J-Quants API取得データそのものを閲覧できる形で配布・シェアすることは禁止。分析結果(チャート/グラフ/レポート等)の共有は可だが、継続反復公開は私的利用外。 |
| J7 | **再配布**(生データ/wrapper API/一括配布)は禁止か | Yes(禁止) | <https://jpx-jquants.com/ja/help/usage> — ブログやインターネット記事 / J-Quants APIを組み込んだアプリ | (本人確認待ち) | API取得データそのものを閲覧できる形で配布・シェアは禁止。ユーザー間でJ-Quantsデータ/分析結果を共有・公開する機能、アプリ運営者サーバでの蓄積/中継は禁止。 |
| J8 | **レート上限**(1日/1分あたり)・課金区分 | 条件付き確認(公開料金表: Free 5件/分, Light 60件/分, Standard 120件/分, Premium 500件/分。本人契約プランは未確認) | <https://jpx-jquants.com/ja> — プラン比較表; <https://jpx-jquants.com/ja/help/plan> — プラン・変更・キャンセルと退会 | (本人確認待ち) | 公開料金表にAPIコール制限と各プランのデータ範囲が掲載。Helpは無料/ライト/スタンダード/プレミアムとアドオン、有料プランの月額課金を説明。本人の現契約プランは別途確認が必要。 |
| J9 | **出典表記(attribution)**の要否(個人内利用/公開時) | 未確認(公開Helpでは明示なし) | <https://jpx-jquants.com/ja/help/usage> — 取得データの分析結果 / YouTube動画 | (本人確認待ち) | 分析結果/手法の公開可、raw直接配布禁止の記述はあるが、attribution必須文言は公開Helpでは確認できない。 |
| J10 | その他の**禁止事項**(スクレイピング・自動売買連携 等) | 条件あり(法人利用・第三者配信・データ利用アプリ提供・継続反復提供・運営者サーバ蓄積/中継は禁止。自動売買連携は未確認) | <https://jpx-jquants.com/ja/help/usage> — 利用目的・ライセンス | (本人確認待ち) | 法人利用、データの第三者配信、データを利用したアプリ提供は営利/非営利を問わず禁止。継続反復の分析結果提供、J-Quants由来データの運営者サーバ蓄積/中継も私的利用外。 |

### B. EDINET DB(Cabocia・REST=edinetdb.com/v1 / MCP=edinetdb.jp/mcp)
原本: 規約 URL = `edinetdb.com/legal/terms`(AI下書き・本人確認待ち) / 契約プラン = **未確認**(本人確認待ち。公開docs上はFree 100/day・Pro 1,000/day)

| # | 設問(Yes/No/条件) | 回答 | 出典URL+節 | 確認日 | 原文の要点 |
|---|---|---|---|---|---|
| E1 | API/MCP のプログラム的利用は許可されているか | Yes(REST API/MCP提供。APIキー条件あり) | <https://edinetdb.com/legal/terms> — 1. Service Description / 4. API and MCP Terms; <https://edinetdb.com/docs/api> — Public REST API; <https://edinetdb.jp/docs/mcp-guide> — 技術仕様 | (本人確認待ち) | サービスはWeb/REST API/MCPで提供。REST/MCPは同じAPIキーでアクセス可。API docsはBase URL/API key header、MCP guideはClaude Code等の接続例を記載。 |
| E2 | 取得データを**ローカルに保存(raw キャッシュ)**してよいか・「一時キャッシュ」の定義/期間 | 条件付きYes(性能目的の一時キャッシュ可。期間は未確認) | <https://edinetdb.com/legal/terms> — 5-1. Permitted Use | (本人確認待ち) | APIレスポンスを性能目的で一時キャッシュすることは可。ただし定期的にAPIから最新データを再取得する条件あり。具体的な保存期間は未記載。 |
| E3 | **保持期間/purge 義務** | 未確認(具体期間なし。定期再取得条件のみ確認) | <https://edinetdb.com/legal/terms> — 5-1. Permitted Use / 12. Distribution of IR-Related PDFs | (本人確認待ち) | 一時キャッシュは定期再取得が条件。ユーザー側rawキャッシュの保持期間/purge義務の具体日数は未確認。IR PDFの3-5年アーカイブ方針はサービス側配布物の説明で、ユーザー保存期間ではない。 |
| E4 | **派生指標の生成・保存**は可か(※AI所見/分析スコア=Cabocia著作物は別扱い) | Yes(条件付き。自分のアプリ/レポート等で処理・分析・利用可。Cabocia著作物は別扱い) | <https://edinetdb.com/legal/terms> — 2. Data Source and Copyright / 4. API and MCP Terms / 5-1. Permitted Use / 9. Intellectual Property and Copyright | (本人確認待ち) | API/MCPデータの商用利用、処理・分析・アプリ/ダッシュボード/レポート利用は可。分析スコア、AI要約、entity resolution等のCabocia独自著作物はCabociaに帰属。 |
| E5 | 取得データを**第三者LLM(Claude/MCP経由含む)に入力**してよいか【致命】 | 条件付き/一部確認: 公式MCPでClaude/ChatGPT接続はdocs化。任意の第三者LLMへraw投入・AI側保持/学習は未確認 | <https://edinetdb.jp/docs/mcp-guide> — Claude Code / Claude Desktop / 技術仕様; <https://edinetdb.com/legal/terms> — 3-2. AI Summaries / 5-3. Commercial Data Provision to Third Parties | (本人確認待ち) | MCP guideはClaude Code/Claude Desktop/Cursor等の接続例を示す。TermsはユーザーのAPI/MCPリクエストpayloadをEDINET DB側の生成AIには渡さないと説明。一方、取得データを任意の第三者LLMへraw投入する一般許諾やAI側保持/学習条件は未確認。 |
| E6 | 送信粒度の条件(raw/要約) | 未確認(公式MCP利用以外のraw/derived/要約粒度条件は不明) | <https://edinetdb.jp/docs/mcp-guide> — 使用例 / 技術仕様; <https://edinetdb.com/legal/terms> — 5-2. Prohibited Use | (本人確認待ち) | MCP tool callで企業検索/スクリーニング等をAIクライアントから利用する例はある。raw/derived/要約別の第三者LLM送信条件は未確認。Webサイトのスクレイピング/AI学習用収集は禁止。 |
| E7 | **再配布**(一括/wrapper API)は禁止か | Yes(一括再配布・wrapper/proxy APIは禁止。B2B/第三者システム統合は別契約) | <https://edinetdb.com/legal/terms> — Point Summary / 5-2. Prohibited Use / 5-3. Commercial Data Provision to Third Parties | (本人確認待ち) | API/MCP取得データの全部または相当部分を第三者へ一括提供・再配布すること、実質同等API(wrapper/proxy)を提供することは禁止。第三者システム/DBへの直接保存・統合は別契約が必要。 |
| E8 | **契約プランの上限**(Pro=1,000/日 で合っているか)・課金 | 条件付き確認(公開docs: Free 100/day, Pro 1,000/day, Business 10,000/day。本人契約プランは未確認) | <https://edinetdb.com/docs/api> — Public REST API / Rate Limits; <https://edinetdb.com/developers> — Pricing Plans; <https://edinetdb.com/legal/terms> — 6. Plans and Billing | (本人確認待ち) | API docsにRate Limits per accountとしてAnonymous/Free 100/day、Pro 1,000/day、Business 10,000/day。Paid plansは月額サブスクでStripe決済。 |
| E9 | **attribution**(公開時の出典表記要請)の具体文言 | Yes(公開サービスは "Powered by EDINET DB" 等の attribution 必須) | <https://edinetdb.com/legal/terms> — Point Summary / 4. API and MCP Terms / 5-2. Prohibited Use | (本人確認待ち) | APIデータを使う公開サービスは "Powered by EDINET DB" 等の出典表記が必要。attributionなしのpublic-facing serviceは禁止事項に含まれる。 |
| E10 | AI所見/分析スコアの利用条件(=INFERENCE固定・FACT化禁止は実装側で担保済) | 条件付き利用可。ただしCabocia著作物・不正確性リスクあり・投資/信用判断の根拠にしない | <https://edinetdb.com/legal/terms> — 2. Data Source and Copyright / 3-2. AI Summaries / 9. Intellectual Property and Copyright | (本人確認待ち) | AI summariesはLLM生成で不正確な可能性があり、投資/信用判断の基礎にしない。AI summaries/financial health score algorithms/entity resolution等はCabocia著作物。実装ではINFERENCE固定。 |

### 解除ゲート(段階・上のワークシートが埋まると自動的に決まる)
> AI下書き時点では、本人が原本で最終確認するまで **FACT化しない**。下の条件が本人確認済みで「可」になった段階だけ解除する。

1. **A1(疎通のみ・raw保存しない・LLMに渡さない)** ← 解除条件: **J1 と E1 が「可」**。
   - キー存在確認 + 最小リクエストで疎通可否を返すだけ。raw を保存せず、取得本文を Claude にも渡さない。
   - AI下書き判定: **J1=条件付きYes / E1=Yes → 本人確認後にA1 GO候補**。本人確認前は判定不能。
2. **B(sync=raw保存)** ← 追加で **J2/J3 と E2/E3 が「可」**(保持/purge 条件を実装に反映)。
   - AI下書き判定: **J2=未確認 / J3=条件あり / E2=条件付きYes / E3=未確認 → NO-GO/判定不能**。J-Quantsは解約/退会・上位プラン変更後の取得済みデータ削除義務があるため、retention/purge 実装が必須。
3. **第三者LLM入力(evidence/research を Claude が読む・MCP利用)** ← 追加で **J5 と E5 が「可」**【最重要】。
   - これが「不可/未確認」の間は、**取得データを分析エージェントに渡さない**(value-audit Phase B/C もここに依存)。
   - AI下書き判定: **J5=未確認かつ高リスク / E5=条件付き・一般raw投入は未確認 → NO-GO/判定不能**。J-Quantsは第三者閲覧・アプリ運営者サーバ蓄積/中継が私的利用外と説明しているため、Claude等へのraw投入は明示許諾確認まで禁止。
4. **公開・配布しない前提の維持** ← **J7/E7 が「再配布禁止」**を確認し、個人内利用に留める(attribution J9/E9 はメモ)。
   - AI下書き判定: **J7=禁止 / E7=禁止 → 個人内利用・非再配布前提は維持必須**。公開/第三者提供は別設計・別確認。

> 補足: **A1 を通すだけなら J1/E1 の確認で足りる**が、実際の分析(財務を Claude に読ませる)には J5/E5(第三者LLM入力)が必須。
> ここが本丸なので、**J5 と E5 を最優先で確認**することを勧める。
