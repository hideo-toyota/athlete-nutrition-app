# 00_ダッシュボード（投球記録）

> このノートは **Dataview** が自動集計します。手入力は不要。vault直下に置き、上のフォルダ名を実際の構成に合わせてください（既定では vault 全体を対象に type で抽出）。

## 🩺 直近14日の体調・回復

```dataview
TABLE weight_kg AS 体重, sleep_score AS 睡眠, resting_hr AS 安静HR, recovery AS 回復, cuff AS カフ, energy AS 気力, thoracic_drill AS 胸椎
FROM #pitching/daily
SORT date DESC
LIMIT 14
```

## ⚾ 直近の投球セッション

```dataview
TABLE session AS 種別, pitch_count AS 球数, intensity AS 強度, velo_max AS 球速MAX, cue AS キュー, output_feel AS 出力感, pain AS 痛み, next_day_cuff AS 翌日カフ
FROM #pitching/throwing
SORT date DESC
LIMIT 12
```

## 🎯 登板の制球効率（自動計算）

```dataview
TABLE innings AS 回, pitch_count AS 球数,
  round(pitch_count / innings, 1) AS "1回球数",
  round((strikes / pitch_count) * 100, 0) + "%" AS ストライク率,
  walks_hbp AS 四死球
FROM #pitching/throwing
WHERE session = "game"
SORT date DESC
```

## 🔥 無痛継続日数（痛み0の連続）

```dataview
TABLE pain AS 投球時痛み, output_feel AS 出力感
FROM #pitching/throwing
WHERE pain > 0
SORT date DESC
LIMIT 5
```
> ↑「痛みが出た直近の投球」。これが空 or 古いほど無痛継続が長い。

## 📈 月次テスト（伝達/パワー/可動域の推移）

```dataview
TABLE velo_max AS 球速MAX, cmj_cm AS CMJ, rmbtv AS RMBTV, thoracic_L AS 胸椎L, thoracic_R AS 胸椎R, trm_deficit AS 回旋左右差
FROM #pitching/monthly
SORT date DESC
```

## 🏋️ 胸椎ドリル継続率（直近14日）

```dataview
TABLE rows.length AS 該当日数
FROM #pitching/daily
WHERE thoracic_drill = true
SORT date DESC
LIMIT 14
```
