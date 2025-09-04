/**
 * Step 1: A列の生書き起こしを分解する基本GAS
 * A列 → B列(イン点), C列(アウト点), D列(文字起こし)
 */

/**
 * メイン分解処理（改良版）
 */
function parseTranscriptionData() {
  const sheet = SpreadsheetApp.getActiveSheet();
  
  Logger.log('=== Step 1: 書き起こし分解開始 ===');
  
  // A列のデータを取得
  const dataRange = sheet.getDataRange();
  const data = dataRange.getValues();
  
  let processedCount = 0;
  let errorCount = 0;
  
  // 結果を格納する配列
  const results = [];
  
  // ヘッダー行を追加
  results.push(['イン点', 'アウト点', '文字起こし']);
  
  // 各行を処理
  for (let i = 0; i < data.length; i++) {
    const cellValue = data[i][0]; // A列の値
    
    // 空のセルや文字列以外はスキップ
    if (!cellValue || typeof cellValue !== 'string') {
      continue;
    }
    
    Logger.log(`処理中 行${i + 1}: ${cellValue.substring(0, 50)}...`);
    
    try {
      // タイムコード範囲を解析
      const parsed = parseTimecodeRange(cellValue);
      
      if (parsed) {
        // 結果配列に追加
        results.push([
          parsed.inPoint,
          parsed.outPoint, 
          parsed.transcription
        ]);
        
        processedCount++;
        Logger.log(`✅ 行${i + 1}: 分解成功`);
        Logger.log(`   イン点: ${parsed.inPoint}`);
        Logger.log(`   アウト点: ${parsed.outPoint}`);
        Logger.log(`   テキスト: ${parsed.transcription.substring(0, 30)}...`);
        
      } else {
        Logger.log(`⚠️  行${i + 1}: タイムコード見つからず - スキップ`);
      }
      
    } catch (error) {
      errorCount++;
      Logger.log(`❌ 行${i + 1}: エラー - ${error.message}`);
    }
  }
  
  // A列をクリア
  sheet.clear();
  
  // 結果を新しくA列から書き込み（空行なし）
  if (results.length > 0) {
    const outputRange = sheet.getRange(1, 1, results.length, 3);
    outputRange.setValues(results);
    
    // ヘッダー行の書式設定
    const headerRange = sheet.getRange(1, 1, 1, 3);
    headerRange.setFontWeight('bold');
    headerRange.setBackground('#E8F4F8');
  }
  
  // 結果レポート
  Logger.log('');
  Logger.log('=== 分解完了 ===');
  Logger.log(`✅ 成功: ${processedCount} 行`);
  Logger.log(`❌ エラー: ${errorCount} 行`);
  Logger.log(`📊 分解結果:`);
  Logger.log(`   A列: イン点タイムコード`);
  Logger.log(`   B列: アウト点タイムコード`);
  Logger.log(`   C列: 文字起こしテキスト`);
  Logger.log(`   空行: 除去済み`);
  
  return { success: processedCount, errors: errorCount };
}

/**
 * タイムコード範囲解析関数
 * @param {string} text - 入力テキスト
 * @returns {Object|null} - {inPoint, outPoint, transcription} または null
 */
function parseTimecodeRange(text) {
  Logger.log(`解析対象: ${text}`);
  
  // タイムコード範囲のパターンマッチング
  // 例: [01:03:35:23 - 01:03:52:00] 今日休み出しに来たこの店は休みです
  
  const timePattern = /\[(\d{2}:\d{2}:\d{2}:\d{2})\s*-\s*(\d{2}:\d{2}:\d{2}:\d{2})\]/;
  const match = text.match(timePattern);
  
  if (!match) {
    Logger.log('タイムコードパターンが見つからない');
    return null; // タイムコードパターンが見つからない
  }
  
  const inPoint = match[1];   // 01:03:35:23
  const outPoint = match[2];  // 01:03:52:00
  
  // タイムコード部分を除去してテキストを抽出
  const transcription = text.replace(timePattern, '').trim();
  
  Logger.log(`  イン点: ${inPoint}`);
  Logger.log(`  アウト点: ${outPoint}`);
  Logger.log(`  文字起こし: "${transcription}"`);
  
  return {
    inPoint: inPoint,
    outPoint: outPoint,
    transcription: transcription
  };
}

/**
 * テスト用関数 - 解析ロジックをテスト
 */
function testParsing() {
  Logger.log('=== 解析テスト開始 ===');
  
  // テストデータ
  const testCases = [
    '[01:03:35:23 - 01:03:52:00] 今日休み出しに来たこの店は休みです',
    '[01:04:13:23 - 01:04:21:15] 見るのも興味があればまあ店舗に入っていただきたい',
    '[01:05:07:23 - 01:05:13:00] 試しにちょっと',
    '無効なデータ - タイムコードなし'
  ];
  
  testCases.forEach((testCase, index) => {
    Logger.log(`テスト ${index + 1}: ${testCase}`);
    
    const result = parseTimecodeRange(testCase);
    
    if (result) {
      Logger.log(`  ✅ イン点: ${result.inPoint}`);
      Logger.log(`  ✅ アウト点: ${result.outPoint}`);
      Logger.log(`  ✅ テキスト: ${result.transcription}`);
    } else {
      Logger.log(`  ❌ 解析失敗`);
    }
    Logger.log('');
  });
}

/**
 * ワンクリック実行 - 分解処理のみ（改良版）
 */
function executeStep1() {
  Logger.log('🚀 Step 1: ワンクリック実行開始');
  
  try {
    // 分解処理実行
    const result = parseTranscriptionData();
    
    Logger.log('');
    Logger.log('🎉 Step 1 完了！');
    Logger.log('結果: A列=イン点, B列=アウト点, C列=文字起こし');
    Logger.log('空行除去済み、元のA列データは不要なのでクリア済み');
    Logger.log('次のステップ: 色分け機能の追加など');
    
    return result;
    
  } catch (error) {
    Logger.log(`💥 実行エラー: ${error.message}`);
    return null;
  }
}