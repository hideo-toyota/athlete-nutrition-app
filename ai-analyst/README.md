# ai-analyst — Discord連携 AI投資分析エージェント(Mac版)

Claude Code × J-Quants × Obsidian × Discord を組み合わせた、個人投資家向けの
半自動データ分析パイプラインの雛形です。

> ⚠️ **免責**: 本プロジェクトは投資助言を目的としたものではありません。特定銘柄の推奨では
> なく、AIと投資データの組み合わせの一体験例です。**過去のバックテストは将来を保証しません。
> 投資判断はすべて自己責任で行ってください。**

---

## これは何か

「個人投資家が抱える3つの壁(時間・知識・感情)」を、AIエージェントで補助するための仕組みです。

- **時間の壁** → 定期実行(launchd)で毎朝自動的にデータ取得・分析
- **知識の壁** → 複数の専門サブエージェントが分担して処理
- **感情の壁** → ルールと記録(Obsidian)で判断を一貫させ、後から振り返る

```
📱 Discord ──指示/通知──┐
                         ▼
🖥️ Mac(常時起動)
   ├─【対話】Claude Code + Discord Channels プラグイン
   └─【定期】launchd → claude -p(ヘッドレス)
              └─ 親エージェント(orchestrator)
                  ├─ 🔧 data-fetcher   : J-Quants からデータ取得
                  ├─ 📊 data-analyst   : 指標計算・可視化
                  ├─ 📈 invest-analyst : シグナル判定・バックテスト
                  ├─ 📝 reporter       : Discord Webhook へ通知
                  └─ 🗂️ recorder       : Obsidian へ判断を記録(mcp-obsidian)
```

---

## ディレクトリ構成

```
ai-analyst/
├── CLAUDE.md                 # Claude Code へのプロジェクト指示(全体方針)
├── README.md                 # このファイル
├── .env.example              # 認証情報のテンプレ(コピーして .env を作る)
├── .gitignore
├── .claude/
│   ├── settings.json         # 自動実行用の権限設定
│   ├── agents/               # サブエージェント定義
│   │   ├── data-fetcher.md
│   │   ├── data-analyst.md
│   │   ├── invest-analyst.md
│   │   ├── reporter.md
│   │   └── recorder.md
│   └── commands/
│       └── daily-report.md   # /daily-report スラッシュコマンド
├── scripts/
│   ├── run_daily.sh          # launchd が叩く起動スクリプト
│   ├── notify.sh             # Discord Webhook 投稿ヘルパー
│   ├── jquants_client.py     # J-Quants API クライアント雛形
│   └── requirements.txt
├── strategies/
│   └── example_momentum.yaml # 投資ルールの例(雛形)
├── data/
│   ├── raw/                  # API 生データ(Git管理外)
│   └── processed/            # 加工済み(Git管理外)
├── reports/                  # 生成レポート履歴(Git管理外)
└── launchd/
    └── com.user.ai-analyst.daily.plist
```

---

## セットアップ手順

### 前提
- macOS / 常時起動できるMac
- [Claude Code](https://docs.claude.com/en/docs/claude-code) を導入し、**Pro/Maxサブスクでログイン済み**
- Python 3.10+ (`python3 --version`)

> 💡 **コスト注意**: サブスクのログインで動きますが、定期実行は使用量を消費します。
> 環境変数 `ANTHROPIC_API_KEY` が設定されていると従量課金APIに切り替わるので、
> サブスクで使う場合は **unset しておく**こと(`echo $ANTHROPIC_API_KEY` で確認)。

### 1. このフォルダをMacへ
```bash
# 例:ホーム直下に配置
cp -R ai-analyst ~/ai-analyst
cd ~/ai-analyst
```

### 2. 認証情報を用意
```bash
cp .env.example .env
# .env を編集して各値を埋める(J-Quants / Discord Webhook など)
```

### 3. Python 依存をインストール
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r scripts/requirements.txt
```

### 4. J-Quants の動作確認
```bash
source .env && export $(grep -v '^#' .env | cut -d= -f1)
python3 scripts/jquants_client.py --check
```
> J-Quants は [公式サイト](https://jpx-jquants.com/)で登録。**無料プランはデータに遅延あり**
> (過去データ中心)。リアルタイム性が必要なら有料プランを検討してください。

### 5. Discord 通知の確認
`.env` に `DISCORD_WEBHOOK_URL` を設定後:
```bash
./scripts/notify.sh "ai-analyst セットアップ完了テスト ✅"
```

### 6. 手動でレポート生成(対話)
Claude Code を起動し、スラッシュコマンドを実行:
```bash
cd ~/ai-analyst
claude
# プロンプト内で:
> /daily-report
```

### 7. 定期実行(launchd)を登録
`launchd/com.user.ai-analyst.daily.plist` 内のパスとユーザー名を自分の環境に修正してから:
```bash
cp launchd/com.user.ai-analyst.daily.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.user.ai-analyst.daily.plist
# 即時テスト:
launchctl start com.user.ai-analyst.daily
```
解除する場合:
```bash
launchctl unload ~/Library/LaunchAgents/com.user.ai-analyst.daily.plist
```

### 8. Mac をスリープさせない設定
- システム設定 → ロック画面/バッテリー →「ディスプレイがオフのときに自動スリープしない」をON
- `run_daily.sh` は `caffeinate` で実行中のスリープを防止済み
- スリープからの自動起床が必要なら:
  ```bash
  sudo pmset repeat wake MTWRF 06:55:00
  ```

---

## 段階導入(おすすめ順)

| Phase | 内容 | ゴール |
|---|---|---|
| 1 | Claude Code + Discord Channels(対話bot) | スマホから手動で分析 |
| 2 | このプロジェクト雛形 + サブエージェント | 親+5サブで分析が回る ← **今ここ** |
| 3 | Discord Webhook 通知 | レポートがDiscordに届く |
| 4 | launchd で定期化 | 毎朝自動でレポート |
| 5 | Obsidian(mcp-obsidian)記録 | 判断を資産化・振り返り |

---

## 関連ツール / ソース

- **Claude Code** (Anthropic) — AIコーディングエージェント
- **J-Quants** (日本取引所グループ公式) — 個人向け株式データAPI
- **Obsidian** — Markdownベース知識管理ツール
- **mcp-obsidian** — Claude × Obsidian 連携 MCP
- 補助ソース例: 株探 PTSランキング、TDnet(適時開示)
