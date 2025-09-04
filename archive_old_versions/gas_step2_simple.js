/**
 * Step 2 シンプル版: 使用可否選択機能
 * D列に「使う/使わない」のシンプル選択
 */

/**
 * 使用可否選択機能の追加
 */
function addUsageSelection() {
  const sheet = SpreadsheetApp.getActiveSheet();
  
  Logger.log('=== Step 2: 使用可否選択機能追加開始 ===');
  
  // 現在のデータ取得
  const dataRange = sheet.getDataRange();
  const data = dataRange.getValues();
  
  if (data.length <= 1) {
    Logger.log('❌ データが不足しています。Step 1を先に実行してください。');
    return;
  }
  
  // D列のヘッダーを追加
  sheet.getRange(1, 4).setValue('使用');
  
  let processedCount = 0;
  
  // デフォルトで全て「使う」に設定
  for (let i = 1; i < data.length; i++) {  // 1行目はヘッダーなので除く
    sheet.getRange(i + 1, 4).setValue('使う');
    processedCount++;
  }
  
  // D列にプルダウン設定（使う/使わない）
  const selectionRange = sheet.getRange(2, 4, data.length - 1, 1);
  const rule = SpreadsheetApp.newDataValidation()
    .requireValueInList(['使う', '使わない'])
    .setAllowInvalid(false)
    .setHelpText('マーカーとして使用するかどうか選択')
    .build();
    
  selectionRange.setDataValidation(rule);
  
  // 条件付き書式設定（使う=緑背景、使わない=灰色背景）
  sheet.clearConditionalFormatRules();
  
  // 「使う」の場合の書式
  const useRule = SpreadsheetApp.newConditionalFormatRule()
    .whenTextEqualTo('使う')
    .setBackground('#E8F5E8')  // 薄い緑
    .setFontColor('#2D5016')   // 濃い緑
    .setRanges([selectionRange])
    .build();
    
  // 「使わない」の場合の書式  
  const dontUseRule = SpreadsheetApp.newConditionalFormatRule()
    .whenTextEqualTo('使わない')
    .setBackground('#F5F5F5')  // 薄い灰色
    .setFontColor('#666666')   // 濃い灰色
    .setRanges([selectionRange])
    .build();
  
  const rules = [useRule, dontUseRule];
  sheet.setConditionalFormatRules(rules);
  
  // ヘッダー行更新
  const headerRange = sheet.getRange(1, 1, 1, 4);
  headerRange.setFontWeight('bold');
  headerRange.setBackground('#E8F4F8');
  
  // カラム幅調整
  sheet.autoResizeColumns(1, 4);
  
  Logger.log('');
  Logger.log('=== Step 2 完了 ===');
  Logger.log(`✅ ${processedCount}行に使用可否選択を追加`);
  Logger.log(`📊 結果:`);
  Logger.log(`   A列: イン点`);
  Logger.log(`   B列: アウト点`);
  Logger.log(`   C列: 文字起こし`);
  Logger.log(`   D列: 使用可否（使う/使わない）`);
  Logger.log(`   デフォルト: 全て「使う」に設定`);
  
  return { processed: processedCount };
}

/**
 * 使用統計表示
 */
function showUsageStats() {
  const sheet = SpreadsheetApp.getActiveSheet();
  const dataRange = sheet.getDataRange();
  const data = dataRange.getValues();
  
  Logger.log('=== 使用統計 ===');
  
  let useCount = 0;
  let dontUseCount = 0;
  
  // D列（使用可否）の統計
  for (let i = 1; i < data.length; i++) {
    const usage = data[i][3];
    if (usage === '使う') {
      useCount++;
    } else if (usage === '使わない') {
      dontUseCount++;
    }
  }
  
  Logger.log(`使う: ${useCount}個`);
  Logger.log(`使わない: ${dontUseCount}個`);
  Logger.log(`合計: ${useCount + dontUseCount}個`);
  Logger.log(`使用率: ${Math.round((useCount / (useCount + dontUseCount)) * 100)}%`);
  
  return { 
    use: useCount, 
    dontUse: dontUseCount, 
    total: useCount + dontUseCount 
  };
}

/**
 * 一括変更機能
 */
function bulkChangeUsage(startRow, endRow, usage) {
  const sheet = SpreadsheetApp.getActiveSheet();
  
  Logger.log(`=== 一括変更: 行${startRow}-${endRow} を "${usage}" に設定 ===`);
  
  if (!['使う', '使わない'].includes(usage)) {
    Logger.log('❌ 使用可否は「使う」または「使わない」を指定してください');
    return false;
  }
  
  const range = sheet.getRange(startRow, 4, endRow - startRow + 1, 1);
  const values = Array(endRow - startRow + 1).fill([usage]);
  range.setValues(values);
  
  Logger.log(`✅ ${endRow - startRow + 1}行を「${usage}」に変更しました`);
  return true;
}

/**
 * ワンクリック実行 - Step 2 シンプル版
 */
function executeStep2Simple() {
  Logger.log('🚀 Step 2 シンプル版: 使用可否選択実行開始');
  
  try {
    const result = addUsageSelection();
    
    // 統計表示
    showUsageStats();
    
    Logger.log('');
    Logger.log('🎉 Step 2 シンプル版完了！');
    Logger.log('D列で「使う/使わない」を選択できます');
    Logger.log('使う=緑背景、使わない=灰色背景で表示');
    Logger.log('デフォルトは全て「使う」に設定済み');
    
    return result;
    
  } catch (error) {
    Logger.log(`💥 実行エラー: ${error.message}`);
    return null;
  }
}

/**
 * 使用する行のみでDaVinci用データ生成
 */
function generateDaVinciData() {
  const sheet = SpreadsheetApp.getActiveSheet();
  const dataRange = sheet.getDataRange();
  const data = dataRange.getValues();
  
  Logger.log('=== DaVinci用データ生成開始 ===');
  
  const results = [];
  
  // ヘッダー追加
  results.push(['timecode', 'marker_name', 'color', 'note', 'duration_frames', 'speaker', 'topic', 'can_cut']);
  
  let markerCount = 0;
  
  // 「使う」が設定された行のみ処理
  for (let i = 1; i < data.length; i++) {
    const usage = data[i][3]; // D列の使用可否
    
    if (usage === '使う') {
      const inPoint = data[i][0];   // A列
      const outPoint = data[i][1];  // B列
      const transcription = data[i][2]; // C列
      
      // デュレーション計算（フレーム）
      const durationFrames = calculateDurationFrames(inPoint, outPoint);
      
      // マーカー名生成
      const markerName = `${String(markerCount + 1).padStart(3, '0')}_${transcription.substring(0, 10)}`;
      
      // ノート（要約）
      const note = transcription.length > 30 ? transcription.substring(0, 27) + '...' : transcription;
      
      results.push([
        inPoint,           // timecode
        markerName,        // marker_name
        'blue',           // color (デフォルト)
        note,             // note
        durationFrames,   // duration_frames
        '出演者',          // speaker
        '一般',           // topic
        'false'           // can_cut (基本は保護)
      ]);
      
      markerCount++;
    }
  }
  
  Logger.log(`✅ ${markerCount}個のマーカーデータを生成`);
  
  return results;
}

/**
 * デュレーション計算（25fps基準）
 */
function calculateDurationFrames(inPoint, outPoint) {
  const [inH, inM, inS, inF] = inPoint.split(':').map(Number);
  const [outH, outM, outS, outF] = outPoint.split(':').map(Number);
  
  const inTotalFrames = (inH * 3600 + inM * 60 + inS) * 25 + inF;
  const outTotalFrames = (outH * 3600 + outM * 60 + outS) * 25 + outF;
  
  return Math.max(outTotalFrames - inTotalFrames, 1);
}