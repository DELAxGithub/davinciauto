/**
 * Step 2: 色分け機能追加
 * D列に話題別色分けを自動追加 + プルダウン設定
 */

/**
 * 色分け機能付きの処理
 */
function addColorClassification() {
  const sheet = SpreadsheetApp.getActiveSheet();
  
  Logger.log('=== Step 2: 色分け機能追加開始 ===');
  
  // 現在のデータ取得
  const dataRange = sheet.getDataRange();
  const data = dataRange.getValues();
  
  if (data.length <= 1) {
    Logger.log('❌ データが不足しています。Step 1を先に実行してください。');
    return;
  }
  
  // D列のヘッダーを追加
  sheet.getRange(1, 4).setValue('話題色');
  
  // DaVinci色リスト
  const davinciColors = [
    'cyan',     // シアン - オープニング
    'rose',     // ローズ - 重要内容  
    'mint',     // ミント - 料理・園芸
    'lemon',    // レモン - コマーシャル
    'lavender', // ラベンダー - 対談・討論
    'sky',      // スカイ - まとめ・終了
    'sand',     // サンド - その他
    'cream'     // クリーム - 一般
  ];
  
  // 背景色マッピング
  const backgroundColors = {
    'cyan': '#00FFFF',
    'rose': '#FF69B4', 
    'mint': '#98FB98',
    'lemon': '#FFFF00',
    'lavender': '#E6E6FA',
    'sky': '#87CEEB',
    'sand': '#F4A460',
    'cream': '#FFFDD0'
  };
  
  let processedCount = 0;
  
  // 各行の文字起こしを分析して色を決定
  for (let i = 1; i < data.length; i++) {  // 1行目はヘッダーなので除く
    const transcription = data[i][2]; // C列の文字起こし
    
    if (transcription && typeof transcription === 'string') {
      // 話題分析
      const topicAnalysis = classifyTopic(transcription);
      
      // D列に色を設定
      sheet.getRange(i + 1, 4).setValue(topicAnalysis.color);
      
      processedCount++;
      Logger.log(`行${i + 1}: "${transcription.substring(0, 20)}..." → ${topicAnalysis.color} (${topicAnalysis.topic})`);
    }
  }
  
  // D列にプルダウン設定
  const colorRange = sheet.getRange(2, 4, data.length - 1, 1);
  const rule = SpreadsheetApp.newDataValidation()
    .requireValueInList(davinciColors)
    .setAllowInvalid(false)
    .setHelpText('話題に応じた色を選択')
    .build();
    
  colorRange.setDataValidation(rule);
  
  // 条件付き書式設定
  sheet.clearConditionalFormatRules();
  
  for (const color of davinciColors) {
    const conditionalFormatRule = SpreadsheetApp.newConditionalFormatRule()
      .whenTextEqualTo(color)
      .setBackground(backgroundColors[color])
      .setRanges([colorRange])
      .build();
    
    const rules = sheet.getConditionalFormatRules();
    rules.push(conditionalFormatRule);
    sheet.setConditionalFormatRules(rules);
  }
  
  // ヘッダー行更新
  const headerRange = sheet.getRange(1, 1, 1, 4);
  headerRange.setFontWeight('bold');
  headerRange.setBackground('#E8F4F8');
  
  // カラム幅調整
  sheet.autoResizeColumns(1, 4);
  
  Logger.log('');
  Logger.log('=== Step 2 完了 ===');
  Logger.log(`✅ ${processedCount}行に色分類を追加`);
  Logger.log(`📊 結果:`);
  Logger.log(`   A列: イン点`);
  Logger.log(`   B列: アウト点`);
  Logger.log(`   C列: 文字起こし`);
  Logger.log(`   D列: 話題色（プルダウン + 背景色連動）`);
  
  return { processed: processedCount };
}

/**
 * 話題分類ロジック
 */
function classifyTopic(text) {
  // キーワードベース分類
  if (text.includes('CM') || text.includes('コマーシャル') || text.includes('広告') || text.includes('スポンサー')) {
    return { color: 'lemon', topic: 'コマーシャル' };
    
  } else if (text.includes('NHK') || text.includes('番組') || text.includes('紹介') || text.includes('開始') || text.includes('始まり')) {
    return { color: 'cyan', topic: 'オープニング' };
    
  } else if (text.includes('料理') || text.includes('レシピ') || text.includes('作り方') || text.includes('食材') || text.includes('調理')) {
    return { color: 'mint', topic: '料理・レシピ' };
    
  } else if (text.includes('花') || text.includes('ガーデン') || text.includes('植物') || text.includes('園芸') || text.includes('栽培')) {
    return { color: 'mint', topic: '園芸・花' };
    
  } else if (text.includes('重要') || text.includes('大切') || text.includes('ポイント') || text.includes('キーポイント') || text.includes('注意')) {
    return { color: 'rose', topic: '重要内容' };
    
  } else if (text.includes('対談') || text.includes('インタビュー') || text.includes('討論') || text.includes('質問') || text.includes('回答')) {
    return { color: 'lavender', topic: '対談・討論' };
    
  } else if (text.includes('まとめ') || text.includes('終了') || text.includes('エンディング') || text.includes('最後') || text.includes('締め')) {
    return { color: 'sky', topic: 'まとめ・終了' };
    
  } else if (text.includes('天気') || text.includes('気温') || text.includes('晴れ') || text.includes('雨') || text.includes('曇り')) {
    return { color: 'sky', topic: '天気・気候' };
    
  } else if (text.length < 10) {
    return { color: 'sand', topic: '短いコメント' };
  }
  
  // デフォルト
  return { color: 'cream', topic: '一般' };
}

/**
 * 色分け統計表示
 */
function showColorStats() {
  const sheet = SpreadsheetApp.getActiveSheet();
  const dataRange = sheet.getDataRange();
  const data = dataRange.getValues();
  
  Logger.log('=== 色分け統計 ===');
  
  const colorCounts = {};
  
  // D列（色）の統計
  for (let i = 1; i < data.length; i++) {
    const color = data[i][3];
    if (color) {
      colorCounts[color] = (colorCounts[color] || 0) + 1;
    }
  }
  
  // 統計表示
  Object.entries(colorCounts).forEach(([color, count]) => {
    Logger.log(`${color}: ${count}個`);
  });
  
  Logger.log(`合計: ${Object.values(colorCounts).reduce((a, b) => a + b, 0)}個`);
  
  return colorCounts;
}

/**
 * ワンクリック実行 - Step 2
 */
function executeStep2() {
  Logger.log('🚀 Step 2: 色分け機能実行開始');
  
  try {
    const result = addColorClassification();
    
    // 統計表示
    showColorStats();
    
    Logger.log('');
    Logger.log('🎉 Step 2 完了！');
    Logger.log('D列に話題別色分けを追加しました');
    Logger.log('プルダウンで色変更可能、背景色も自動変更されます');
    
    return result;
    
  } catch (error) {
    Logger.log(`💥 実行エラー: ${error.message}`);
    return null;
  }
}

/**
 * 色のテスト（特定のテキストでテスト）
 */
function testColorClassification() {
  Logger.log('=== 色分類テスト ===');
  
  const testTexts = [
    '今日の料理は簡単なパスタです',
    'NHK総合の番組をご紹介します', 
    'これは重要なポイントです',
    'コマーシャルの時間です',
    '花の栽培について',
    'インタビューを開始します',
    'それではまとめに入ります',
    'あー、そうですね',
    '天気は晴れです'
  ];
  
  testTexts.forEach((text, index) => {
    const result = classifyTopic(text);
    Logger.log(`テスト${index + 1}: "${text}"`);
    Logger.log(`  → ${result.color} (${result.topic})`);
  });
}