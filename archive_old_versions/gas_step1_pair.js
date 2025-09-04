/**
 * Step 1 修正版: ペアデータ処理
 * タイムコード行 + 文字起こし行を結合して処理
 */

/**
 * ペアデータ処理メイン関数
 */
function parseTranscriptionPairs() {
  const sheet = SpreadsheetApp.getActiveSheet();
  
  Logger.log('=== Step 1: ペアデータ処理開始 ===');
  
  // 全データ取得
  const dataRange = sheet.getDataRange();
  const data = dataRange.getValues();
  
  Logger.log(`総行数: ${data.length}`);
  
  // 結果格納配列
  const results = [];
  
  // ヘッダー追加
  results.push(['イン点', 'アウト点', '文字起こし']);
  
  let processedCount = 0;
  let skippedCount = 0;
  
  // ペア処理
  for (let i = 0; i < data.length - 1; i++) {
    const currentRow = data[i][0];
    const nextRow = data[i + 1][0];
    
    // 空行スキップ
    if (!currentRow || !nextRow) {
      continue;
    }
    
    Logger.log(`行${i + 1}-${i + 2}をペア処理中...`);
    Logger.log(`  行${i + 1}: "${currentRow}"`);
    Logger.log(`  行${i + 2}: "${nextRow}"`);
    
    // タイムコードパターン検証
    const timePattern = /\[(\d{2}:\d{2}:\d{2}:\d{2})\s*-\s*(\d{2}:\d{2}:\d{2}:\d{2})\]/;
    const timeMatch = currentRow.match(timePattern);
    
    if (timeMatch) {
      // 現在行がタイムコード、次行が文字起こしの想定
      const inPoint = timeMatch[1];
      const outPoint = timeMatch[2];
      const transcription = nextRow.toString().trim();
      
      // 次行がタイムコードでないことを確認
      const nextIsTimeCode = timePattern.test(nextRow);
      
      if (!nextIsTimeCode && transcription.length > 0) {
        results.push([inPoint, outPoint, transcription]);
        processedCount++;
        
        Logger.log(`  ✅ ペア処理成功:`);
        Logger.log(`     イン点: ${inPoint}`);
        Logger.log(`     アウト点: ${outPoint}`);
        Logger.log(`     文字起こし: ${transcription.substring(0, 30)}...`);
        
        // 次の行はスキップ（既に処理済み）
        i++;
        
      } else {
        Logger.log(`  ⚠️  次行もタイムコードまたは空 - スキップ`);
        skippedCount++;
      }
      
    } else {
      Logger.log(`  ⚠️  タイムコードパターンなし - スキップ`);
      skippedCount++;
    }
  }
  
  // シートクリアして結果書き込み
  sheet.clear();
  
  if (results.length > 0) {
    const outputRange = sheet.getRange(1, 1, results.length, 3);
    outputRange.setValues(results);
    
    // ヘッダー書式設定
    const headerRange = sheet.getRange(1, 1, 1, 3);
    headerRange.setFontWeight('bold');
    headerRange.setBackground('#E8F4F8');
    
    // カラム幅自動調整
    sheet.autoResizeColumns(1, 3);
  }
  
  // 結果レポート
  Logger.log('');
  Logger.log('=== ペア処理完了 ===');
  Logger.log(`✅ 成功: ${processedCount} ペア`);
  Logger.log(`⚠️  スキップ: ${skippedCount} 行`);
  Logger.log(`📊 結果:`);
  Logger.log(`   A列: イン点タイムコード`);
  Logger.log(`   B列: アウト点タイムコード`);
  Logger.log(`   C列: 文字起こしテキスト`);
  
  return { success: processedCount, skipped: skippedCount };
}

/**
 * より厳密なペア処理（連続性チェック付き）
 */
function parseTranscriptionPairsStrict() {
  const sheet = SpreadsheetApp.getActiveSheet();
  
  Logger.log('=== Step 1: 厳密ペア処理開始 ===');
  
  const dataRange = sheet.getDataRange();
  const data = dataRange.getValues();
  
  const results = [];
  results.push(['イン点', 'アウト点', '文字起こし', '元行番号']);
  
  let processedCount = 0;
  const timePattern = /\[(\d{2}:\d{2}:\d{2}:\d{2})\s*-\s*(\d{2}:\d{2}:\d{2}:\d{2})\]/;
  
  for (let i = 0; i < data.length; i++) {
    const currentCell = data[i][0];
    
    if (!currentCell || typeof currentCell !== 'string') continue;
    
    const timeMatch = currentCell.match(timePattern);
    
    if (timeMatch) {
      // タイムコード行見つけた -> 次の有効行を探す
      let transcriptionFound = false;
      
      for (let j = i + 1; j < Math.min(i + 4, data.length); j++) {
        const candidateText = data[j][0];
        
        if (candidateText && 
            typeof candidateText === 'string' && 
            candidateText.trim().length > 0 && 
            !timePattern.test(candidateText)) {
          
          // 文字起こしテキストとして採用
          const inPoint = timeMatch[1];
          const outPoint = timeMatch[2];
          const transcription = candidateText.trim();
          
          results.push([inPoint, outPoint, transcription, `${i + 1}-${j + 1}`]);
          processedCount++;
          
          Logger.log(`✅ ペア発見: 行${i + 1} + 行${j + 1}`);
          Logger.log(`   ${inPoint} - ${outPoint}`);
          Logger.log(`   ${transcription.substring(0, 40)}...`);
          
          transcriptionFound = true;
          break;
        }
      }
      
      if (!transcriptionFound) {
        Logger.log(`⚠️  行${i + 1}: 対応する文字起こし未発見`);
      }
    }
  }
  
  // 結果出力
  sheet.clear();
  
  if (results.length > 0) {
    const outputRange = sheet.getRange(1, 1, results.length, 4);
    outputRange.setValues(results);
    
    // ヘッダー書式
    const headerRange = sheet.getRange(1, 1, 1, 4);
    headerRange.setFontWeight('bold');
    headerRange.setBackground('#E8F4F8');
    
    sheet.autoResizeColumns(1, 4);
  }
  
  Logger.log(`=== 厳密処理完了: ${processedCount}ペア処理 ===`);
  
  return { success: processedCount };
}

/**
 * ワンクリック実行 - ペア処理版
 */
function executeStep1Pair() {
  Logger.log('🚀 Step 1 ペア処理版: 実行開始');
  
  try {
    // 標準ペア処理実行
    const result = parseTranscriptionPairs();
    
    Logger.log('');
    Logger.log('🎉 Step 1 ペア処理完了！');
    Logger.log('結果: A列=イン点, B列=アウト点, C列=文字起こし');
    Logger.log('タイムコード行 + 文字起こし行のペア処理済み');
    
    return result;
    
  } catch (error) {
    Logger.log(`💥 実行エラー: ${error.message}`);
    
    // エラー時は厳密処理を試行
    Logger.log('厳密処理にフォールバック...');
    return parseTranscriptionPairsStrict();
  }
}

/**
 * デバッグ: ペアパターンを分析
 */
function analyzeDataPattern() {
  const sheet = SpreadsheetApp.getActiveSheet();
  const dataRange = sheet.getDataRange();
  const data = dataRange.getValues();
  
  Logger.log('=== データパターン分析 ===');
  
  const timePattern = /\[(\d{2}:\d{2}:\d{2}:\d{2})\s*-\s*(\d{2}:\d{2}:\d{2}:\d{2})\]/;
  
  for (let i = 0; i < Math.min(data.length, 20); i++) {
    const cellValue = data[i][0];
    
    if (cellValue && typeof cellValue === 'string') {
      const isTimeCode = timePattern.test(cellValue);
      const isEmpty = cellValue.trim().length === 0;
      
      Logger.log(`行${i + 1}: ${isTimeCode ? '🕐タイムコード' : '📝テキスト'} "${cellValue.substring(0, 40)}${cellValue.length > 40 ? '...' : ''}"`);
    } else {
      Logger.log(`行${i + 1}: ❌空行`);
    }
  }
}