# CLAUDE_HANDOFF_kabutan_quality_gates_spec.md — kabutan レーン品質ゲート SPEC(Q11・前倒し発行)

- doc-id: `CLAUDE_HANDOFF_kabutan_quality_gates_spec`
- as_of: 2026-07-10
- writer: クラウド裁定者(cloud adjudicator)
- 位置: `ai-business-radar/radar-ops/CLAUDE_HANDOFF_kabutan_quality_gates_spec.md`
- 上位規約: `ANALYSIS_QUALITY_RULES.md` / 経緯: lunch・preclose 連続訂正(2026-07-10)と再発認定
- 状態: **発行(実装 GO)**。恒久修正クラスにつき月次投入ゲート例外。書き手宣言のうえ着手。

---

## 0. 目的
kabutan 自動分析の投稿前に、**決定論の検証器**で「数値の再現」「ラベルの昇格」「実装外の検証計画」を機構的に遮断する。書き手(LLM)の注意力に依存しない再発防止。

## 1. ゲートA — 数値再計算(deterministic recount)
- 新規 `scripts/automation/kabutan_post_validate.py`(+テスト)。`kabutan_analysis_headless.sh` の stdin 投稿経路で、**生成後・投稿前**に挟む。
- 分析本文は末尾に機械可読の主張マニフェスト(`<!--CALC ... -->` ブロック)を出力する様式に変更:
  - 件数主張: `{predicate: "<述語完全形>", count: N, codes: [...]}`(**述語は省略しない** — `up_5pct_vs_confirmed_close` / `low_momentum_reversal_watch` 等)
  - 実数引用: `{code, field, value}`(momentum・始値比等)
  - 時系列主張: `{from_slot, to_slot, transition: {...}}`
- 検証器は当該スロット(および時系列主張があれば前スロット)の observer JSON から**再計算し、全件一致しなければ NO_POST**(理由をログ・marker は書かない=既存の marker 規律)。
- 参考実装: Codex の scratch jq 2本(flag recalc / lunch→preclose 遷移行列・2026-07-10)。

## 2. ゲートB — ラベル昇格阻止(label lint)
- flags 由来の件数・集合 → `[CALCULATION]` 必須。見出し由来の記述 → `[THIRD_PARTY_REPORT]` 必須(「株探見出しがそう報じた」までが事実)。
- **企業行動の断定(量産開始/提携/決算値等)は公式開示の照合なしに書けない** — 照合前は見出し表現のまま THIRD_PARTY_REPORT。
- **再現・検証は分類を変えない**(信頼度のみ。CALCULATION は検証済みでも CALCULATION)。
- 選抜標本からの市場全体主張(breadth/二極化)は `[UNKNOWN]` 併記がなければ NO_POST。
- 実装: 検証器内のパターン lint(禁止語+必須ラベルの対応表)。完全な意味検査は求めない — 定型違反の機構的遮断が目的。

## 3. ゲートC — 能力マニフェスト照合(capability manifest)
- 新規正本 `radar-ops/CAPABILITY_MANIFEST.md`: 実装済み取得能力の一覧(J-Quants=個別日足・銘柄マスタ・財務サマリー/**日次配信・寄与度分解なし**。kabutan observer のフィールド一覧。日経公式 Daily Summary=システム外の人間照合先。EDINET=本照合には不使用)。
- 検証計画・答え合わせ節が**マニフェスト外の能力を参照したら NO_POST**(例: 「J-Quants で寄与度確認」)。
- マニフェストは INDEX §7 に追加し sha 照合対象とする。改版は裁定者。

## 4. 様式D — 関係4段階表示(relation tiers)
- 銘柄と材料の結合には必ず段階タグ: **発行企業 / 発表内の名指し相手 / 業種peer / loose theme**。
- 検証器は結合記述に段階タグ必須を lint。業種は静的業種マスタ(既存 derived)参照で SUMCO 型の誤分類を防ぐ。
- タグなし・当事者でない銘柄の値動きを材料反応として記述 → NO_POST。

## 5. 暫定措置との接続
- ゲート稼働まで: 「因果較正」「保有読替」2節は観測限定文型に降格(preclose 裁定 §4)。
- **解除条件 = 本 SPEC の DoD 達成**をもって両節は検証様式付きで復帰。

## 6. 実装割当・DoD
- 書き手: **既定=司令塔**(automation は司令塔ドメイン)。Codex が実装する場合は書き手宣言を先に(対象: `kabutan_post_validate.py`・`kabutan_analysis_headless.sh` の挿入行・プロンプトテンプレート・テスト)。
- テスト: (a) 件数不一致で NO_POST (b) 一致で通過 (c) ラベル欠落/昇格違反で NO_POST (d) マニフェスト外参照で NO_POST (e) 段階タグ欠落で NO_POST (f) 正常系フル通過。+投稿ゼロ実発火テスト。
- DoD: ①フルスイート回帰 OK ②合成の違反ケースが NO_POST でログに理由 ③実スロット1回が検証器経由で POSTED_OK ④CONFIRM_ 報告。
- 停止条件: 検証器が正常な投稿を誤って恒常遮断(偽陽性の連発)→ 検証器を fail-open にせず**投稿停止のまま**裁定者へ差し戻し(サイレント素通りの方が害が大きい)。
