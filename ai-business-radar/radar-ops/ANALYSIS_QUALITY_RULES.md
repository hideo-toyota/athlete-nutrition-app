# ANALYSIS_QUALITY_RULES.md — 分析品質規約(正本)

- doc-id: `ANALYSIS_QUALITY_RULES`
- version: v2
- as_of: 2026-07-22
- writer: クラウド裁定者（cloud adjudicator。binding本文のcanonical issuer）
- binding_intake: `956da7d56c6767e4c7b775c438b53cad7419528f`
- binding_baseline_ruling: `6d7edab0e834e310964de6bac5b0a33f9e1832bd`
- canonical_baseline: `86cd36a70f66b8ea7a73a58e9c2ae8b47eb9e0cd`
- supersedes_on_effective: v1 sha256 `bf82eb2f9b5cdf3ebdbd497abc64d92ec474b56817c50d73f5223c77e876fcb0`
- 位置: `ai-business-radar/radar-ops/ANALYSIS_QUALITY_RULES.md`（正本）
- 適用: 全レーン（司令塔・実行役・自動レーン群・監査役・裁定者）の**すべての分析・記述・投稿・記録**に無条件で適用する。ROLES/ROADMAP/session-starters は本規約に優先しない（矛盾時は本規約が優先）。
- 発効条件: 本文のbyte-hash付き`CLAUDE_HANDOFF_` binding裁定、ownerによる直接配備またはownerが明示指定したcommander単独writerによる正本配備、配備後bytesに対するクラウド裁定者の`CLAUDE_HANDOFF_` read-back受理がすべて完了した時点で発効する。commanderが発行する`CONFIRM_`はdeployment receiptであり、裁定者artifactのprefixではない。draft、intake、binding裁定またはdeployment receiptだけを実装GO・売買承認・発注承認へ読み替えない。

---

## R0. 目的
本プロジェクトは、オーナーの適法な個人投資研究において、オーナー資本の継続性を守りながら、オーナーが別途定めるリスク、drawdown、流動性、leverage、capacityおよび注意可能性の制約内で、全適用cost控除後の利益および事前登録benchmarkに対するalphaの獲得を**目標として支援**する。現時点の `alpha_status` と `investable_alpha` はともに `NOT_PROVEN` であり、利益、alpha、元本維持または損失回避を保証しない。主対象期間は短期1〜2週間および中期3〜12か月とし、変更は別SPECで明示する。

成果物は、`EVIDENCE_ONLY` の計器・観測と、R2に適合する `OWNER_DECISION_SUPPORT` を含み得る。ただし、AIが利益を保証すること、Claudeが裁量で個別化された売買案を生成すること、注文を代行すること、または人間の承認を推定することは含まない。最終的な資金配分と注文は、対象、instrument、side、数量、価格条件および有効期限を特定して、その都度オーナーが明示的に承認する。

利益目的は、FACTの捏造、UNKNOWNの隠蔽、PIT違反、コストの省略、risk制約の迂回、sealed testの覗き見、不利な結果の削除、秘密・有料本文・raw本文への接触、既存HOLDまたは裁定レーンの迂回を正当化しない。

## R1. FACT / CALCULATION / INFERENCE / UNKNOWN の四分離（必須）
- すべての主張は次のいずれかに分類し、**分類を明示**する。
  - **FACT**: 一次ソース（APIレスポンス・CSV・ファイル・ログ・実測ヘッダ）で今この場で検証できる事実。出典とas_ofを添える。
  - **CALCULATION**: FACTを決定論的な式またはコードで変換した値。入力FACT、式またはコード参照/version、as_ofおよび入力hashを添える。`OWNER_DECISION_SUPPORT`で銘柄候補、side、rank、entry/exit、価格またはsizeに用いるCALCULATIONは、さらにR2.2の事前登録rule_id、rule_version、registration artifact hashを必須とする。CALCULATIONをFACT、INFERENCEまたは推奨として表示しない。
  - **INFERENCE**: FACTまたはCALCULATIONから導いた推論。前提となるFACT/CALCULATIONを必ず併記する。
  - **UNKNOWN**: 観測手段を持たない、または未実測の事項。**推測で埋めない**。「わからない」を消さない。
- 欠損は前日値・近傍値・それらしい既定値で**埋めてはならない**。欠損は理由付きでUNKNOWNと表示する（例: 米国地合いM0のFRED未着系列）。

## R2. 出力クラス、generator分離および禁止事項

### R2.1 既定クラス
- 全レーンの既定は `output_class=EVIDENCE_ONLY` とする。
- `EVIDENCE_ONLY` は観測、検証、教育、監査、一般レポート、公開出力、自動レーン、Discord、headlessを含む。このクラスでは、個別銘柄の推奨、売買方向、期待収益順位、entry/exit水準、価格目標・価格レンジ、position sizeを出さない。
- `output_class=OWNER_DECISION_SUPPORT` は、オーナーとの非公開直接対話かつ別途binding受理された `OWNER_RULE_CALCULATION` contract、またはそのcontractが指定する私的保存先に限定する。公開、自動、Discord、教育、headless、webhookまたは注文経路へ配送してはならない。
- `OWNER_RULE_CALCULATION` contractへbindingされていない既存レーンは、すべて`EVIDENCE_ONLY`である。現行session-starterまたはレーンSPECの推奨・候補・順位・価格目標禁止は不変とする。
- 本v2だけを根拠に既存validator、禁止語、guard、配送経路または権限設定を緩めてはならない。既存レーンは、別SPECと別GOで明示的に移行されるまで従来の厳しい制約を維持する。

### R2.2 C-1 generator分離（必須）
`OWNER_DECISION_SUPPORT` で扱えるgeneratorを次に限定する。

1. `generator_class=OWNER_PREREGISTERED_DETERMINISTIC_RULE`
   - オーナーが対象runの出力または評価結果を観測する前に、rule_id、rule_version、入力、変換、universe、threshold、weight、tie-break、rank_basis、horizon、cost、entry/exitまたはsize算式、失効条件を事前登録した決定論コードまたは機械ルール。V4/V5では`rule_registered_at < earliest_decision_input_available_at`かつ`latest_decision_input_available_at <= calculated_at <= created_at < outcome_first_available_at`（`latest`は全decision inputの`available_at`の最大値）を機械確認し、time inversion時は停止する。V2/V3ではrule、dataset、期間splitおよびsealed対象hashを評価またはsealed開封前に固定する。
   - その機械出力は、銘柄候補、LONG/SHORT/NO-TRADE、比較順位、条件付き水準、価格レンジまたはposition sizeを含み得るが、すべて `CALCULATION` としてrule_id、rule_version、as_of、入力hashを付ける。
   - Claudeは、登録済みルールの実行、出力の忠実な転記、根拠分類、証拠状態の採点、重要UNKNOWN、risk注意および将来rule-version向けの追加falsifier候補を付記できる。追加falsifier候補はcreated_atを記録し、当該runまたは既知outcomeのscoreへ遡及適用しない。Claudeは、結果観測後にuniverse、threshold、weight、tie-break、side、rank、horizonまたは出力値を裁量で補完、変更、並べ替え、選別または救済してはならない。
2. `generator_class=OWNER_DECISION_RECORD`
   - オーナー自身が行った判断、承認または見送りを、そのまま記録し、事前登録済みbenchmarkとcostモデルで遡及採点する。
   - Claudeは、オーナーが明示していないside、数量、価格条件、理由または承認を推測して補ってはならない。

Claudeセッションの裁量判断による、個別化された銘柄候補、LONG/SHORT指示、比較順位、entry/exit/target水準、価格または価格レンジ、position-size案または注文条件の新規作成、選択、変更もしくは補完は、私的対話を含め**禁止**する。オーナー指令、利益目的、R2改訂またはV5表示を、この禁止の解除として扱わない。決定論ruleが算出した結果は「Claudeの推奨」「AI選定」と呼ばず、`OWNER_RULE_CALCULATION`と表示する。

### R2.3 必須フィールド
`OWNER_DECISION_SUPPORT` packetは、少なくとも次を持つ。

- `artifact_id`、`schema_version`、`created_at`、`packet_hash`
- `output_class=OWNER_DECISION_SUPPORT`、`distribution=OWNER_PRIVATE_ONLY`
- `generator_class`、`rule_id`、`rule_version`、事前登録時刻・登録artifact hash
- データの`as_of`、`available_at`、取得元、鮮度、PIT適合、入力hash
- 対象universe、eligibility、除外理由、候補数、instrument、horizon
- FACT、CALCULATION、INFERENCE、UNKNOWN、base rate、sample size、不確実性、OOS/holdout状態
- benchmark、gross estimate、控除したcost、未算入cost、net estimate
- commission、exchange/clearing fee、tax、bid-ask spread、slippage、market impact、margin/funding interest、borrow fee、recall/buy-in、配当相当額、futures roll/basisの各適用状態
- entry、exit、expiry、falsifier、downside、stress、gap risk、最大想定損失
- liquidity、ADV比、turnover、concentration、portfolio exposure、gross/net exposure
- `validation_level`、`evidence_status`、`decision_eligibility`
- `owner_item_review_status`（V0〜V4=`NOT_APPLICABLE`、V5表示前=`REQUIRED`、owner記録後=`GO|NO_GO|EXPIRED`）、`owner_decided_at`および`owner_decision_recorded_at`（未記録=`NOT_APPLICABLE`、ownerがdecision時刻を明示しない記録では`owner_decided_at=UNKNOWN`）、`execution_status=NOT_AUTHORIZED`

費用項目は、非該当なら理由付き`NOT_APPLICABLE`、未取得なら`UNKNOWN`とし、ゼロで暗黙補完しない。重要cost、portfolio、価格、borrow、marginまたは市場snapshotがUNKNOWNまたはstaleなら推測で埋めず、V3以上への昇格、V5 `OWNER_ITEM_REVIEW`およびcapital sizingを停止する。

`generator_class=OWNER_DECISION_RECORD`では、事前登録ruleに紐づく採点でない限りrule関連フィールドを理由付き`NOT_APPLICABLE`とする。オーナーが明示しなかったside、数量、価格条件、理由または承認はUNKNOWNのまま残し、推測で補完しない。その他の非該当フィールドも暗黙欠損にせず`NOT_APPLICABLE`を明示する。

### R2.4 Validation ladder
- `V0 OBSERVATION`: 観測のみ。売買案、期待収益順位およびcapital sizingへ使用しない。
- `V1 OWNER_PREREGISTERED_RULE`: rule bytes/hash、universe、benchmark、full-cost vector、falsifier、variant family、train/validation/sealed-OOS/prospective期間境界を評価前に固定。research-only。
- `V2 RETROSPECTIVE_PAPER`: PIT-cleanな過去検証を実施。paper-only。sealed OOSを未通過。
- `V3 SEALED_OOS_PAPER`: sealed OOS、事前登録benchmark、全適用cost、multiple-testing管理、PITおよびappend-onlyを通過。paper-only。
- `V4 PROSPECTIVE_PAPER`: 事前登録したprospective paper運用で較正、失敗例を含めappend-onlyで採点。V4/V5は`rule_registered_at < earliest_decision_input_available_at`かつ`latest_decision_input_available_at <= calculated_at <= created_at < outcome_first_available_at`（`latest`は全decision inputの`available_at`の最大値）を機械確認し、time inversion時は停止する。
- `V5 OWNER_ITEM_REVIEW`（旧称`LIVE_ELIGIBLE`）: V4と独立risk審査を通過したexact deterministic packetを、オーナーのitem単位GO/NO-GO記録対象として非公開表示できる状態。V5はlive、capitalまたはtrading eligibilityではなく、自動発注権、broker送信権、POST権またはClaudeの裁量generator権を発生させない。

V-levelはevidence maturityであって、収益性、alpha証明、売買指示または実行権限ではない。V0〜V4はlive useを許可しない。現行artifactのV5 itemはゼロである。現時点の証拠状態は `alpha_status=NOT_PROVEN` および `investable_alpha=NOT_PROVEN` とする。v2の発効、候補の存在、V0〜V4の完了、sealed OOS、prospective paperまたは単一モデルの高成績を、別のbinding alpha-proof裁定なしにalpha証明へ読み替えない。

### R2.5 信用・空売り・先物
信用、空売りまたは先物を含む機械ルール出力では、通常の必須フィールドに加え、適用可能なborrow availability、borrow cost、逆日歩、recall、金利、初期・維持証拠金、追証、強制決済、gap risk、最大損失、限月、倍率、basis、roll cost、夜間流動性を明示する。必要値がUNKNOWNの場合は`RESEARCH_ONLY`または`PAPER_ONLY`に留め、capital sizingを出さない。現物レーンのGOを信用、空売りまたは先物へ継承しない。

### R2.6 人間承認と配送境界
- AI、commander、executor、自動レーンまたはvalidatorは `execution_status=AUTHORIZED` を設定できない。
- V5のGO/NO-GOは`OWNER_DECISION_RECORD`であり、GOでも`execution_status`を変更しない。
- 実注文の承認は、オーナーだけがinstrument、side、venue、order type、価格条件、数量、最大損失、packet version/hash、有効期限を特定して行う。いずれかが変われば承認は失効する。
- 分析結果からbroker API、POST、Discord、webhook、注文画面送信または外部公開へ直結することは、チャネル別SPEC、型付きschema、投稿前validator、監査logおよび別のbinding GOが揃うまで禁止する。

### R2.7 禁止事項（FORBIDDEN）
- Claudeの裁量判断による個別化された銘柄候補、LONG/SHORT指示、比較順位、entry/exit水準、価格レンジまたはposition-size案。
- 利益保証、「必ず上がる」「負けない」「安全」等の断定、または不確実性を隠す表現。
- outcome確認後のrule、rank_basis、falsifier、horizonまたは仮説の無記録変更。
- universe、除外、cost、benchmark、不利な結果、non-fillまたは失敗例の秘匿。
- staleまたは将来情報をcurrent/PIT情報として使うこと、sealed testの覗き見、証拠状態の過大表示。
- 人間承認の推定・代行、自動発注、broker送信、無人運用、無断POSTまたは外部送信。
- 秘密（APIキー・webhook URL・token・.env実値）、有料本文、raw HTML、raw response本文を**読まない・保存しない・出力しない**。状態表記（`SET`/`EMPTY`/`ABSENT`）のみ許容。
- 上記に触れる必要が生じたら**停止**して人間判断へ戻す。

## R3. PIT（Point-In-Time）と append-only
- 生成物は**生成時点の観測**として記録し、**既存日を上書きしない**（PIT追記）。
- 台帳・journal（`education_ledger.jsonl`等）は**append-only**。誤りは行削除ではなく**訂正行（void_*/正典再掲）**で是正し、矛盾を「無かったこと」にしない。
- rule登録、rule改版、owner decision、owner approval、取消、supersessionおよびscoreはPIT append-onlyとし、既存行を上書きしない。rule変更は新versionとし、観測済みas_ofへ遡及適用しない。
- sealed OOSは、事前登録済み`variant_family + dataset_hash + split_hash`ごとに一度だけ開封する。初回開封後、そのdataset/periodは全rule_version、改名familyおよび派生variantに対してsealedではなくなる。後続version/familyのsealed評価には、未観測の新しいdataset/period/hashを要する。opener、opened_atおよび全variant結果をappend-onlyで記録し、再開封、再封印、version変更またはfamily改名による再利用を禁止する。
- 読取り時刻ガード: 確定前の値（ナイトセッション中の暫定値など）を確定値として保存しない（M0 SOURCE_CONTRACTの06:00 JST以降ガード参照）。

## R4. 出典・鮮度・as_of の三分離
- 出典（source）・観測as_of（データの時点）・記録as_of（書いた時点）を分けて書く。
- `source_as_of`、`observed_at`、`rule_registered_at`、`calculated_at`、`owner_decided_at`、`scored_at`を分離する。
- 計器値には**取得時刻を行内明示**する（brief冒頭の「今日読む」packet等、鮮度が意味を持つ場面で必須）。

## R5. value-audit の出力様式（ISSUE_MAP連動）
- value-auditは`ISSUE_MAP.md`の**7論点の順に7節**で出力する。欠けた論点は**UNKNOWN明記**（節を省略しない）。
- 判断記録の理由は**論点番号**で記載する（判断記録レーン=`CLAUDE_HANDOFF_judgment_record_lane.md`）。
- value-audit自体を候補生成gatewayまたは`OWNER_RULE_CALCULATION` generatorへ変更しない。

## R6. 停止条件（Stop Conditions）
次のいずれかで**即時停止・差し戻し**する。

- 単一as_ofの読みが複数箇所で不一致（読み取り層の整合性違反）。
- readiness/DoDの偽OK（未達を達成と表示）。
- 隔離処理が正常行を巻き込む。
- 既存出力形式の非互換破壊（バイト等価または**明示的改善**のみ許容）。
- 秘密・有料本文・raw本文に触れる必要が生じた。
- 裁定範囲外への着手要求（推測で前提を作る要求を含む）。
- **S-1 C-1 conflict**: C-1 generator分離への抵触、Claude裁量出力を事前登録済み機械ルール出力と偽る記述、未登録rule、観測後のrule変更、registration/input hash欠落、rule version不明、またはEVIDENCE_ONLYからの候補化。
- **S-2 INDEX mismatch**: INDEXまたはpacket manifestのhash、size、lines、base参照の不一致。
- **S-3 GO reinterpretation**: v2、V5または裁定を実装GO、alpha証明、売買承認、POST承認または発注承認へ読み替える記述。
- **S-4 scope creep**: canonicalコード、validator、POST、LaunchAgent、broker、発注、資金利用へのscope creep。
- **S-5 missing supersession**: supersession表の欠落または既存HOLDの無断解除。
- **S-6 adjudicator push request**: 裁定者にcanonical pushを要求すること。
- 判断支援必須フィールドの欠落、証拠状態の過大表示、失効済みsnapshot、benchmarkまたは適用costの欠落。
- short/credit/futuresでborrow、margin、roll、最大損失等の必須条件がUNKNOWNのままV5 `OWNER_ITEM_REVIEW`またはcapital sizingを出すこと。
- outcome確認後の無記録な順位基準変更、候補脱落、失敗例除外またはsealed test汚染。
- V5 `owner_item_review_status`の欠落・`EXPIRED`、実注文に必要なowner承認の欠落・期限切れ、packet改変、NAV・保有・建玉・流動性・risk上限のUNKNOWNまたは違反。

## R7. 検証と正直な申告
- 実装には**テスト**を添える。テスト不能部は**投稿ゼロの実発火テスト**等で代替し、代替した旨を申告する。
- 判断支援実装には、許可された事前登録済み機械ルールpacketのpositive testと、Claude裁量generator、保証表現、stale data、PIT違反、cost欠落、universe欠落、time inversion、証拠状態過大表示、無断実行、外部投稿漏出、shortのborrow欠落を拒否するnegative testを添える。
- 既存のEVIDENCE_ONLY、自動、公開、Discord、教育およびheadlessレーンは、別SPECで明示的に移行されるまで従来の禁止validatorを維持する。
- **逸脱・未達・データ品質の瑕疵は自主開示**する（scored_at誤記・writer欄欠落・偽「投稿済み」記録などの実例を隠さない）。
- 「完了」表現はDoD接地でのみ用いる。当日未生成を「当日分析完了」と書かない。

## Supersession と非干渉
| v1条項 | v2での扱い |
|---|---|
| R0 | 利益・after-cost benchmark超過を経済目的として明文化し、EVIDENCE_ONLYと限定的OWNER_DECISION_SUPPORTを区別して全面置換。 |
| R1 | 三分類へCALCULATIONを追加し、一般CALCULATIONには決定論provenanceを要求し、`OWNER_DECISION_SUPPORT`のtrade-field CALCULATIONだけR2.2事前登録chainを追加要求する。FACT/INFERENCE/UNKNOWNの趣旨は維持。 |
| R2 | 一律禁止を、EVIDENCE_ONLY既定、C-1 generator分離、事前登録済み機械ルール出力、オーナー判断記録、Validation ladderおよび配送禁止へ全面置換。 |
| R3〜R5 | 趣旨を維持。表記を整形。 |
| R6 | v1停止条件を維持し、C-1、hash、GO読替え、scope creep、supersession、証拠・risk・承認の停止条件を追加。 |
| R7 | v1検証義務を維持し、判断支援positive/negative testと既存validator維持を追加。 |

- 過去のincident裁定、lift裁定、判断記録仕様、ISSUE_MAP、旧`CODEX_R2_STRUCTURED_ANALYSIS_SPEC_DRAFT_20260714.md`および各レーンSPECは編集せず、その履歴上の意味を遡及変更しない。本改訂scope-idは`QUALITY_RULE_R2_AMENDMENT`であり、旧draftをsupersedeしない。
- `CLAUDE_HANDOFF_` binding裁定、owner直接またはowner指定commander単独writerによる正本配備、および配備後bytesに対する裁定者の`CLAUDE_HANDOFF_` read-back受理が完了するまで、`ANALYSIS_QUALITY_RULES.md` v1を置換しない。発効後も過去記録を遡及変更せず、将来向けにのみ本表の条項をsupersedeする。
- 本v2は、managed deploymentおよびR-C2の既存記録・状態を変更しない。R-C2=`PARTIAL`、Candidate B=`HOLD (0/96)`、Candidate E=`EXECUTION NO-GO`、FA-1/TA-1=`HOLD`を維持し、新規managed/admin操作、exact2、F4、pilot、recompute、promotion、POST、LaunchAgent/launchctl、broker/order routingその他未発行GO=`NONE`を解除しない。
- 本v2は、canonical code/behavior実装、validator変更、tests実行、data/outputs変更、POST、LaunchAgent/launchctl、pilot、recompute、promotion、broker接続、発注または資金利用を許可しない。各作業はexact write-set、単一writer、独立verifier、別binding GOを要する。

## 参照
- 役割・接頭辞・署名: `ROLES_current.md`
- 論点定義: `ISSUE_MAP.md`
- 工程・順序: `ROADMAP_current.md`
- 判断記録・月次投入ゲート: `CLAUDE_HANDOFF_judgment_record_lane.md` / `CLAUDE_HANDOFF_monthly_intake_gate.md`
