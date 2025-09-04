/**
 * データ配置修正用GAS
 * 書き起こしテキスト消失問題の解決
 */

/**
 * 正しいデータ配置に修正
 * A列: 色選択 | B列: 書き起こしテキスト
 */
function fixDataLayout() {
  const sheet = SpreadsheetApp.getActiveSheet();
  
  Logger.log('=== データ配置修正開始 ===');
  
  // 現在の状況確認
  const dataRange = sheet.getDataRange();
  const data = dataRange.getValues();
  
  Logger.log(`現在の行数: ${data.length}`);
  
  // 修正方針の説明
  Logger.log('修正方針:');
  Logger.log('1. 元の書き起こしデータを復元または再入力');
  Logger.log('2. A列=色、B列=書き起こしテキストの配置に整理');
  Logger.log('3. プルダウン設定を正しく適用');
  
  // 手動修正指示
  Logger.log('');
  Logger.log('⚠️  手動操作が必要です:');
  Logger.log('1. 書き起こしデータをB列に再度貼り付けてください');
  Logger.log('2. その後 setupCorrectLayout() を実行してください');
}

/**
 * 正しい配置での初期セットアップ
 */
function setupCorrectLayout() {
  const sheet = SpreadsheetApp.getActiveSheet();
  
  Logger.log('=== 正しいレイアウト設定開始 ===');
  
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
  
  // 対応する背景色
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
  
  // データ範囲確認
  const dataRange = sheet.getDataRange();
  const numRows = dataRange.getNumRows();
  
  // A列にプルダウン設定（色選択用）
  const colorRange = sheet.getRange(1, 1, numRows, 1);
  const rule = SpreadsheetApp.newDataValidation()
    .requireValueInList(davinciColors)
    .setAllowInvalid(false)
    .setHelpText('DaVinci色を選択')
    .build();
    
  colorRange.setDataValidation(rule);
  
  // 条件付き書式設定（A列のみ）
  sheet.clearConditionalFormatRules(); // 既存ルールクリア
  
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
  
  // B列の書き起こしテキストから色を自動分類
  autoClassifyFromColumn();
  
  Logger.log('✅ 正しいレイアウト設定完了');
  Logger.log('   A列: 色プルダウン + 背景色');
  Logger.log('   B列: 書き起こしテキスト');
}

/**
 * B列のテキストから色を自動分類してA列に設定
 */
function autoClassifyFromColumn() {
  const sheet = SpreadsheetApp.getActiveSheet();
  const data = sheet.getDataRange().getValues();
  
  let updateCount = 0;
  
  for (let i = 0; i < data.length; i++) {
    const transcriptionText = data[i][1]; // B列
    
    if (!transcriptionText || typeof transcriptionText !== 'string') continue;
    
    // テキスト分析
    const cleanText = transcriptionText.replace(/\[.*?\]\s*/, '').trim();
    const topicAnalysis = classifyTopic(cleanText);
    
    // A列に色設定
    sheet.getRange(i + 1, 1).setValue(topicAnalysis.color);
    updateCount++;
  }
  
  Logger.log(`✅ B列から${updateCount}行の色を自動分類`);
}

/**
 * 話題分類関数（再利用）
 */
function classifyTopic(text) {
  if (text.includes('CM') || text.includes('コマーシャル') || text.includes('広告')) {
    return { color: 'lemon', topic: 'コマーシャル' };
  } else if (text.includes('NHK') || text.includes('番組') || text.includes('紹介') || text.includes('開始')) {
    return { color: 'cyan', topic: 'オープニング' };
  } else if (text.includes('料理') || text.includes('レシピ') || text.includes('作り方')) {
    return { color: 'mint', topic: '料理・レシピ' };
  } else if (text.includes('花') || text.includes('ガーデン') || text.includes('植物')) {
    return { color: 'mint', topic: '園芸・花' };
  } else if (text.includes('重要') || text.includes('大切') || text.includes('ポイント')) {
    return { color: 'rose', topic: '重要内容' };
  } else if (text.includes('対談') || text.includes('インタビュー') || text.includes('討論')) {
    return { color: 'lavender', topic: '対談・討論' };
  }
  
  return { color: 'cyan', topic: '一般' };
}

/**
 * 修正版変換処理（正しいデータ配置対応）
 */
function convertWithCorrectLayout() {
  const sheet = SpreadsheetApp.getActiveSheet();
  const data = sheet.getDataRange().getValues();
  
  Logger.log('=== 修正版変換開始 ===');
  
  // 結果格納用
  const markers = [];
  
  // ヘッダー
  markers.push([
    'timecode', 'marker_name', 'color', 'note', 'duration_frames', 'speaker', 'topic', 'can_cut'
  ]);
  
  let processedCount = 0;
  
  for (let i = 0; i < data.length; i++) {
    const selectedColor = data[i][0]; // A列の色
    const transcriptionText = data[i][1]; // B列のテキスト
    
    if (!transcriptionText || typeof transcriptionText !== 'string') continue;
    
    // タイムコード解析
    const timeMatch = transcriptionText.match(/\[(\d{2}:\d{2}:\d{2}:\d{2})\s*-\s*(\d{2}:\d{2}:\d{2}:\d{2})\]/);
    if (!timeMatch) continue;
    
    const inPoint = timeMatch[1];
    const outPoint = timeMatch[2];
    const cleanText = transcriptionText.replace(/\[.*?\]\s*/, '').trim();
    
    // マーカー情報生成
    const markerName = `${String(i + 1).padStart(3, '0')}_${cleanText.substring(0, 10)}`;
    const note = cleanText.length > 30 ? cleanText.substring(0, 27) + '...' : cleanText;
    const durationFrames = calculateDuration(inPoint, outPoint);
    const canCut = selectedColor === 'rose' ? 'false' : 'true';
    
    markers.push([
      inPoint,           // timecode
      markerName,        // marker_name
      selectedColor,     // color
      note,              // note
      durationFrames,    // duration_frames
      '出演者',           // speaker
      selectedColor,     // topic
      canCut            // can_cut
    ]);
    
    processedCount++;
  }
  
  // 結果シート作成
  createResultSheet(markers);
  
  Logger.log(`✅ 変換完了: ${processedCount}個のマーカー生成`);
}

/**
 * デュレーション計算
 */
function calculateDuration(inPoint, outPoint) {
  const [inH, inM, inS, inF] = inPoint.split(':').map(Number);
  const [outH, outM, outS, outF] = outPoint.split(':').map(Number);
  
  const inTotalFrames = (inH * 3600 + inM * 60 + inS) * 25 + inF;
  const outTotalFrames = (outH * 3600 + outM * 60 + outS) * 25 + outF;
  
  return Math.max(outTotalFrames - inTotalFrames, 1);
}

/**
 * 結果シート作成
 */
function createResultSheet(markers) {
  const spreadsheet = SpreadsheetApp.getActiveSpreadsheet();
  
  // 既存シート削除
  const existingSheet = spreadsheet.getSheetByName('DaVinci用CSV');
  if (existingSheet) {
    spreadsheet.deleteSheet(existingSheet);
  }
  
  // 新シート作成
  const resultSheet = spreadsheet.insertSheet('DaVinci用CSV');
  
  // データ書き込み
  if (markers.length > 0) {
    const range = resultSheet.getRange(1, 1, markers.length, markers[0].length);
    range.setValues(markers);
    
    // ヘッダー書式
    const headerRange = resultSheet.getRange(1, 1, 1, markers[0].length);
    headerRange.setFontWeight('bold');
    headerRange.setBackground('#E8F4F8');
  }
  
  // 自動調整
  resultSheet.autoResizeColumns(1, markers[0].length);
  
  Logger.log('✅ 結果シート "DaVinci用CSV" 作成完了');
}