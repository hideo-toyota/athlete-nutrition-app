# Singularity Society BootCamp #4 応募用メモ

このファイルは応募フォームへ貼り付けるための下書きです。公開URLだけは、GitHub / Vercel / Netlify / デモ動画などに公開した後で差し替えてください。

アプリの仕様、使い方、活用方法は [APP_SPEC_AND_USER_GUIDE.md](APP_SPEC_AND_USER_GUIDE.md) にまとめています。

## 提出URL

以下のうち1つ以上をフォームに貼る想定です。

- GitHubリポジトリ: `TODO: 公開GitHub URLを貼る`
- 公開デモURL: `TODO: Vercel / Netlify / GitHub Pages などのURLを貼る`
- デモ動画URL: `TODO: YouTube限定公開 / Loom / Google Drive などのURLを貼る`

## あなたの実績や活動内容がわかるもの

Athlete Nutrition App という、アスリート向けの食事・体調・本番前後の栄養管理プロトタイプを Vibe Coding で作成しました。

このアプリは、単なるカロリー記録ではなく、競技・本番日・疲労感・睡眠・食欲・体重を組み合わせて、選手が「今日何を食べるべきか」「本番に向けて何を準備すべきか」「周囲が何を支援すべきか」を見える化することを目的にしています。

現時点で実装済みの内容は以下です。

- 陸上、野球、サッカー、バレエ、バスケットボール、ゴルフ、水泳、卓球の競技プロフィール切り替え
- 通常日、練習日、試合前日、試合当日、回復日の Day Mode 管理
- 食事プラン作成、実行チェック、写真添付、カレンダー記録
- 睡眠、疲労、食欲、体重、メモのコンディションログ
- 本番日から逆算した Event Fueling / カーボローディング計算
- Buddy Check、Pair Score、Cheer Stamps によるCtoC継続支援
- Team Food Log と Reminder Scheduler による仲間同士の食事共有・声かけ
- AI Coach Notes によるルールベースの改善コメント
- 保護者・コーチ向け共有メモ生成
- TypeScript / production build / Playwright E2E による動作確認

スポーツ栄養については、ACSM / Academy of Nutrition and Dietetics / Dietitians of Canada の Nutrition and Athletic Performance をベースに、糖質・たんぱく質の体重あたり目標値、カーボローディング、回復期の補給を簡易モデル化しています。

## 応募フォーム用の短い説明

競技・本番日・体調に合わせて、アスリートの食事計画、実行チェック、振り返り、仲間や保護者との共有までを支援するコンディショニングアプリです。React / TypeScript / Vite で作成し、localStorage で日別データを保存します。

特徴は、試合や本番日をカレンダーに登録すると、そこから逆算してカーボローディング、当日補給、翌日回復の糖質・たんぱく質目標を体重あたりで計算できる点です。さらに疲労感、睡眠、食欲も補正に使い、現場で実行しやすい提案に寄せています。

本人だけでなく、バディ、チームメイト、保護者、コーチが支援しやすいよう、CtoCの相互確認、リマインド、共有メモも入れています。

## 推奨する提出URL構成

一番強い提出は、以下の3点セットです。

1. 公開GitHubリポジトリ
2. 公開WebデモURL
3. 1-2分の操作デモ動画

時間がない場合は、最低限 `公開GitHubリポジトリ + READMEのスクリーンショット`、または `公開WebデモURL` のどちらか1つを用意してください。

## 公開前チェックリスト

- GitHubリポジトリを public にする
- README に概要、機能、実行方法、検証結果を書く
- `npm run build` が通ることを確認する
- `dist/index.html` または Vercel / Netlify / GitHub Pages で公開する
- 応募フォームのURL欄に公開URLを貼る
- 個人情報や不要な検証データが入っていないことを確認する

## ローカル確認コマンド

```bash
cd "/Users/toyodahideo/Pictures/アスリートアプリ"
npm install
npm run dev
```

## 検証済みコマンド

```bash
npx tsc --noEmit
npm run build
node e2e-temp/verify2.mjs
node e2e-temp/verify3.mjs
node e2e-temp/focus-photo.mjs
node e2e-temp/content-verify.mjs
node e2e-temp/five-athlete-30day-verify.mjs
node e2e-temp/event-fueling-verify.mjs
```

## 注意事項

栄養ターゲットは教育・デモ用途の簡易目安です。実際の個別栄養指導では、年齢、性別、体組成、既往歴、血液検査、発汗量、競技レベルなどを含む専門的評価が必要です。
