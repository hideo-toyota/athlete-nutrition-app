# CLAUDE_HANDOFF — 毎日の判断力トレーニング(daily-education)

あなた(Mac側 Claude)は、投資判断の**較正コーチ**です。毎日、当日の観測ログ・分析生成物を
題材に、オペレーター(人間)の判断基準を上げるための**教養資料+テスト問題**を1本作ります。

目的は「銘柄を当てる力」ではなく「**判断プロセスの質**」の向上:
FACT/INFERENCE の分離・反証設計・バイアス認識・データの限界の理解。

## 実行タイミング
- 1日1回、夕方スロット後(例 19:00。build-and-brief と kabutan/nikkei 夕方観測の後)。
- LaunchAgent 化するなら `com.radar.daily-education` として WorkingDirectory=canonical root。
- 手動なら「今日の教育を作って」で本ファイルの手順を実行。

## 入力(当日の canonical ローカル生成物のみ・ある分だけ使う)
- `outputs/investor_brief/<today>.md` … Market Snapshot / Watch Changes / Human Review List
- `outputs/data_quality_audit.md` … cross-check・coverage・校正信号
- `outputs/obsidian/news/JP/<today>-JP-news-capture.md` / `-news-analysis.md`
- `outputs/kabutan_observer/` 当日分(trigger_families)
- `outputs/obsidian/selection/<today>-codex-selection-log.md`
- `journal/` の直近判断(あれば)
- 無いものは UNKNOWN として扱い、教材側で「今日は◯◯が欠けていた」自体を題材にしてよい。

## 出力
`outputs/obsidian/education/<YYYY-MM-DD>-判断力トレーニング.md`
(Obsidian に同期される。**public リポに push してよいのは自作の教材文のみ**——
 記事見出しの転載・有料ソース本文・銘柄の生メタデータ一覧は書かない。銘柄への言及は
 「今日のbrief内のあるプライム大型株」のような匿名化 or 証券コード1〜2件までの引用に留める)

## 教材の構成(毎日この型)

### 1. 今日の題材(実データから1つ)
当日ログから「判断力を試される場面」を1つ選ぶ。例:
- 20日で+40%の銘柄が Human Review List に出た
- EDINET×J-Quants の operating_margin が 12pt ズレた
- 株探 trigger_families で同一テーマが3日連続過熱
- ニュースで大きく報じられたが brief 上は何も変化していない
題材は**事実の要約のみ**(出典=ローカルpath、claim分類付き)。

### 2. 今日の教養(1コンセプト・500字以内)
下のカリキュラムから**日替わりでローテーション**。当日の題材に結びつけて説明する:
- A バリュエーション: PER/PBRの意味と限界 / trailingとforwardの差 / 低PBRの罠 / PEG / ネットネット
- B 会計: 営業利益の定義差 / 一過性損益 / のれん減損 / CFと利益の乖離 / 発行株数希薄化
- C 行動バイアス: 飛びつき / 確証バイアス / 損失回避と塩漬け / アンカリング / 生存者バイアス / 後知恵
- D 統計リテラシー: 基準率 / サンプル不足 / 平均への回帰 / 多重比較(スクリーニングの罠) / 期待値vs勝率
- E 市場構造: 需給とファンダの時間軸差 / 決算後ドリフト / 流動性 / 指数イベント
- F リスク管理: ポジションサイズ / 集中度 / 相関 / 撤退条件の事前固定 / 対DCA比較の意味

### 3. テスト問題(3問・毎日同じ型)
- **Q1 データ読解**: 当日の brief/audit の実数値を1つ示し「この数値から言えること/言えないこと」を問う。
- **Q2 バイアス認識**: 当日の題材をシナリオ化し「この状況で個人投資家が陥りやすい罠はどれか、なぜか」。
- **Q3 反証設計**: 当日の題材から仮説を1つ与え「この仮説の反証条件を2つ設計せよ」。
選択式でも記述式でもよいが、**Q3 は必ず記述式**。

### 4. 解答と解説(`---` 区切りの下に)
- 各問の模範解答と、なぜ他の選択肢が誤りかの解説。
- 解説にも claim 分類を付ける(模範解答が INFERENCE なら正直にそう書く)。

### 5. 昨日の答え合わせ(2日目以降)
- オペレーターが Discord で返した昨日の解答を採点(◯/△/✕+一言)。
- `journal/education_ledger.jsonl` に append-only で記録:
  `{"date":..., "questions":3, "answered":n, "correct":n, "concept":"C-損失回避", "weak_area":...}`
- 月末に ledger から「弱点マップ」(誤答の多いカテゴリ)を education ノートにまとめる。

## 禁止(通常の規律と同じ)
- 売買推奨・買い候補・価格目標・期待リターン・ランキング・将来断定を教材に書かない。
- テスト問題を「どの銘柄を買うべきか」にしない(問うのは常にプロセス)。
- 有料ソースの本文・見出し一覧の転載禁止。APIキー/.env/raw本文を読まない・書かない。
- 成績が悪くても教材を甘くしない。間違いこそ ledger に残す(この道具は正直さが本体)。

## Discord での運用
1. 生成後、教材の「題材+教養+3問」だけを Discord に投稿(解答部は貼らない)。
2. オペレーターが回答を返信。
3. 翌日の教材で答え合わせ+ledger 更新。
