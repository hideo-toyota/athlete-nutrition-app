import { SportProfile } from '../types'

const GENERAL_REFERENCES = [
  {
    label: 'ACSM/AND 2016',
    title: 'Nutrition and Athletic Performance',
    url: 'https://pubmed.ncbi.nlm.nih.gov/26920240/'
  },
  {
    label: 'ISSN Protein 2017',
    title: 'International Society of Sports Nutrition Position Stand: protein and exercise',
    url: 'https://pubmed.ncbi.nlm.nih.gov/28642676/'
  }
] as const

export const SPORT_PROFILES: SportProfile[] = [
  {
    id: 'track',
    label: '陸上・ランニング',
    category: 'Endurance / Speed-Endurance',
    summary: '高強度セッションやレース前後で筋グリコーゲンの確保が重要です。女性・持久系では鉄不足にも注意します。',
    carbTargets: {
      normal: { min: 5, max: 6 },
      practice: { min: 6, max: 8 },
      pre_game: { min: 7, max: 10 },
      game: { min: 6, max: 8 },
      recovery: { min: 5, max: 7 }
    },
    proteinTarget: { min: 1.4, max: 1.8 },
    focusNutrients: ['炭水化物', 'たんぱく質', '鉄', '水分'],
    hydrationNote: '高温時や二部練では水分と電解質を早めに補います。',
    cautionNote: '持久系では低エネルギー状態や鉄不足がパフォーマンス低下につながります。',
    fuelingNote: 'レース前日は主食量を増やし、当日は消化の軽い補食を外さない設計が有効です。',
    references: [
      ...GENERAL_REFERENCES,
      {
        label: 'Middle-distance Review',
        title: 'Contemporary Nutrition Interventions to Optimize Performance in Middle-Distance Runners',
        url: 'https://pubmed.ncbi.nlm.nih.gov/30299184/'
      }
    ]
  },
  {
    id: 'baseball',
    label: '野球',
    category: 'Batting / Intermittent Power',
    summary: '長い試合時間の中で、集中力を切らさない補食と水分管理が重要です。瞬発系でも糖質不足は避けます。',
    carbTargets: {
      normal: { min: 4, max: 5 },
      practice: { min: 5, max: 7 },
      pre_game: { min: 6, max: 8 },
      game: { min: 5, max: 7 },
      recovery: { min: 4, max: 6 }
    },
    proteinTarget: { min: 1.4, max: 1.8 },
    focusNutrients: ['炭水化物', 'たんぱく質', '水分', 'ナトリウム'],
    hydrationNote: '試合間隔が長いので、ベンチで少量ずつ飲める設計が向いています。',
    cautionNote: '練習量の割に食事が軽くなりやすく、総エネルギー不足を見逃しやすい競技です。',
    fuelingNote: 'イニング間に入れやすい炭水化物と、試合後のたんぱく質回復を両立させます。',
    references: [
      ...GENERAL_REFERENCES,
      {
        label: 'Baseball Intake 2024',
        title: 'Survey of nutritional intake status in college baseball players',
        url: 'https://pubmed.ncbi.nlm.nih.gov/39898580/'
      },
      {
        label: 'Team Sport Review',
        title: 'Dietary Intakes of Professional and Semi-Professional Team Sport Athletes Do Not Meet Sport Nutrition Recommendations',
        url: 'https://pmc.ncbi.nlm.nih.gov/articles/PMC6567121/'
      }
    ]
  },
  {
    id: 'soccer',
    label: 'サッカー',
    category: 'High-Intensity Team Sport',
    summary: '反復スプリントと長時間走行に対応するため、試合前日から糖質を厚くし、回復食も早めに入れます。',
    carbTargets: {
      normal: { min: 5, max: 7 },
      practice: { min: 6, max: 8 },
      pre_game: { min: 7, max: 10 },
      game: { min: 6, max: 8 },
      recovery: { min: 5, max: 7 }
    },
    proteinTarget: { min: 1.4, max: 1.8 },
    focusNutrients: ['炭水化物', 'たんぱく質', 'ナトリウム', '水分'],
    hydrationNote: '発汗量が多い日はナトリウムを含むドリンクを併用します。',
    cautionNote: '試合前後で糖質不足になると、走行量・反応速度・回復の質が落ちやすいです。',
    fuelingNote: '前日から主食量を積み、当日は小分け補食で血糖を安定させます。',
    references: [
      ...GENERAL_REFERENCES,
      {
        label: 'Soccer Review 2018',
        title: 'Nutrition and Supplementation in Soccer',
        url: 'https://pmc.ncbi.nlm.nih.gov/articles/PMC5968974/'
      }
    ]
  },
  {
    id: 'ballet',
    label: 'バレエ',
    category: 'Aesthetic / Technical',
    summary: '見た目の要求が強い一方で、低エネルギー利用可能性、鉄、カルシウム、ビタミンDの管理が重要です。',
    carbTargets: {
      normal: { min: 4, max: 5 },
      practice: { min: 5, max: 6 },
      pre_game: { min: 5, max: 6 },
      game: { min: 5, max: 6 },
      recovery: { min: 4, max: 5 }
    },
    proteinTarget: { min: 1.4, max: 1.8 },
    focusNutrients: ['総エネルギー量', '鉄', 'カルシウム', 'ビタミンD'],
    hydrationNote: '長時間リハーサルでは気づかないうちに脱水しやすく、こまめな補水が必要です。',
    cautionNote: '低エネルギー利用可能性は骨・月経・回復に影響しやすく、体重だけで評価しない設計が重要です。',
    fuelingNote: '量より頻度で支え、乳製品や魚、赤身肉、大豆食品で鉄と骨代謝を支えます。',
    references: [
      ...GENERAL_REFERENCES,
      {
        label: 'Dancer Review 2024',
        title: 'What Do We Know About the Energy Status and Diets of Pre-Professional and Professional Dancers',
        url: 'https://pubmed.ncbi.nlm.nih.gov/39770914/'
      }
    ]
  },
  {
    id: 'basketball',
    label: 'バスケットボール',
    category: 'High-Intensity Court Sport',
    summary: '高い解糖系負荷と反復ジャンプ・接触に備え、糖質と回復たんぱく質を切らさない設計が中心です。',
    carbTargets: {
      normal: { min: 5, max: 6 },
      practice: { min: 6, max: 8 },
      pre_game: { min: 6, max: 8 },
      game: { min: 6, max: 8 },
      recovery: { min: 5, max: 7 }
    },
    proteinTarget: { min: 1.4, max: 1.8 },
    focusNutrients: ['炭水化物', 'たんぱく質', 'ナトリウム', '水分'],
    hydrationNote: '室内競技でも発汗は大きく、試合後の再水和が回復に直結します。',
    cautionNote: '連戦ではグリコーゲン回復が追いつきにくく、試合後早期の補給が重要です。',
    fuelingNote: '練習・試合後の数時間で糖質とたんぱく質を戻すと、次のパフォーマンスが安定します。',
    references: [
      ...GENERAL_REFERENCES,
      {
        label: 'Basketball Review 2022',
        title: 'In-Season Nutrition Strategies and Recovery Modalities to Enhance Recovery for Basketball Players',
        url: 'https://pmc.ncbi.nlm.nih.gov/articles/PMC9023401/'
      }
    ]
  },
  {
    id: 'golf',
    label: 'ゴルフ',
    category: 'Skill / Long-Duration',
    summary: 'ラウンドが長く、集中力維持が重要なため、脱水と低血糖を避ける持続的な補給設計が向いています。',
    carbTargets: {
      normal: { min: 3, max: 5 },
      practice: { min: 4, max: 5 },
      pre_game: { min: 4, max: 6 },
      game: { min: 4, max: 6 },
      recovery: { min: 3, max: 5 }
    },
    proteinTarget: { min: 1.2, max: 1.6 },
    focusNutrients: ['炭水化物', 'たんぱく質', '水分', 'ナトリウム'],
    hydrationNote: '歩行ラウンドでは気づかない脱水が起こりやすく、前半から飲み始める方が安定します。',
    cautionNote: '競技強度は極端に高くなくても、長時間の歩行と集中で補食不足が技術精度に響きます。',
    fuelingNote: '前半・後半で小さく炭水化物を挟み、血糖の乱高下を避ける構成が相性良いです。',
    references: [
      ...GENERAL_REFERENCES,
      {
        label: 'Golf Review 2024',
        title: 'Nutrition and Golf Performance: A Systematic Scoping Review',
        url: 'https://pubmed.ncbi.nlm.nih.gov/39347918/'
      }
    ]
  },
  {
    id: 'swimming',
    label: '水泳',
    category: 'Aquatic Endurance / Power',
    summary: '二部練や高ボリューム練習では糖質需要が大きく、水中競技でも脱水対策が必要です。',
    carbTargets: {
      normal: { min: 5, max: 7 },
      practice: { min: 6, max: 10 },
      pre_game: { min: 7, max: 10 },
      game: { min: 6, max: 8 },
      recovery: { min: 5, max: 7 }
    },
    proteinTarget: { min: 1.4, max: 2.0 },
    focusNutrients: ['炭水化物', 'たんぱく質', '水分', 'ナトリウム'],
    hydrationNote: '水中では喉の渇きを自覚しにくいので、練習前から補水計画を置きます。',
    cautionNote: '朝練や二部練では総摂取量が不足しやすく、食べる回数を増やす設計が有効です。',
    fuelingNote: '練習直後に糖質とたんぱく質を入れて、次のセッションまでの回復時間を稼ぎます。',
    references: [
      ...GENERAL_REFERENCES,
      {
        label: 'Swimming Review 2018',
        title: 'Nutritional needs in the professional practice of swimming: a review',
        url: 'https://pmc.ncbi.nlm.nih.gov/articles/PMC5772075/'
      },
      {
        label: 'Power Sports 2011',
        title: 'Nutrition for power sports: middle-distance running, track cycling, rowing, canoeing/kayaking, and swimming',
        url: 'https://pubmed.ncbi.nlm.nih.gov/21793766/'
      }
    ]
  },
  {
    id: 'table_tennis',
    label: '卓球',
    category: 'Racket / Repeated Sprint-Skill',
    summary: '試合自体は短くても複数試合が続きやすく、素早い回復と集中力維持のための小分け補給が有効です。',
    carbTargets: {
      normal: { min: 4, max: 5 },
      practice: { min: 5, max: 6 },
      pre_game: { min: 5, max: 7 },
      game: { min: 5, max: 7 },
      recovery: { min: 4, max: 5 }
    },
    proteinTarget: { min: 1.4, max: 1.8 },
    focusNutrients: ['炭水化物', 'たんぱく質', '水分', 'ナトリウム'],
    hydrationNote: '短時間競技でも大会は長くなりやすく、軽い補食を切らさない方が集中が安定します。',
    cautionNote: '一食を重くすると動きづらいので、複数試合日は軽く速く入る補食が向いています。',
    fuelingNote: 'バナナやゼリー、飲むヨーグルトなどで、試合間に小さく戻す設計が実用的です。',
    references: [
      ...GENERAL_REFERENCES,
      {
        label: 'Table Tennis 2023',
        title: 'Nutrition Recommendations for Table Tennis Players-A Narrative Review',
        url: 'https://pubmed.ncbi.nlm.nih.gov/36771479/'
      }
    ]
  }
]
