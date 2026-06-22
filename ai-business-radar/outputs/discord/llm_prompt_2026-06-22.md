# Discord LLM Prompt — 2026-06-22

以下のローカル分析packetを読み、投資助言ではなく調査メモとして要約してください。

- packet: `outputs/llm_handoff/2026-06-22.md`
- evidence_blocks: 50
- jquants_blocks: 0

必須ルール:
- まず UNKNOWN / 不足データを列挙する。
- FACT / CALCULATION / INFERENCE / ASSUMPTION / UNKNOWN を分ける。
- 検証対象の仮説、反証条件、次に読む資料を短く出す。
- discipline check 未通過であり、最終判断は人間と明記する。
- 売買指示、価格目標、順位付け、利益保証、将来断定は禁止。
- provider raw本文、APIキー、.env、認証情報を要求しない。

出力形式:
1. UNKNOWN / 不足
2. 検証対象の仮説(断定しない)
3. 反証条件
4. 次に読む資料
5. claim分類表
6. discipline gate 注意
