/**
 * デバッグ用: 文字起こし消失問題の調査
 */

/**
 * 現在のシートの内容を詳細調査
 */
function debugSheetContent() {
  const sheet = SpreadsheetApp.getActiveSheet();
  const dataRange = sheet.getDataRange();
  const data = dataRange.getValues();
  
  Logger.log('=== シート内容詳細調査 ===');
  Logger.log(`総行数: ${data.length}`);
  
  for (let i = 0; i < Math.min(data.length, 5); i++) {
    Logger.log(`行${i + 1}:`);
    Logger.log(`  A列: "${data[i][0]}" (型: ${typeof data[i][0]})`);
    Logger.log(`  B列: "${data[i][1]}" (型: ${typeof data[i][1]})`);
    Logger.log(`  C列: "${data[i][2]}" (型: ${typeof data[i][2]})`);
    Logger.log('');
  }
}

/**
 * 特定のサンプルテキストで解析テスト
 */
function testSpecificSample() {
  Logger.log('=== 特定サンプルテスト ===');
  
  // 実際のデータサンプル
  const samples = [
    '[00:59:59:23 - 01:00:14:22] どちらの小寺さんでいらっしゃるかは、偶然です、あの、アニー、アニーです、あ、ほら、ちょっとね、りんちゃんに私もちょっと',
    '[01:00:15:23 - 01:00:38:20] 基本は、このカガダにして、指示が来て、人間が出て、マイクを持ってくる、なるほど、あと、お兄さんはお疲れちが',
    '[01:00:39:23 - 01:00:41:21] こうやって、添景操作で、そうです',
    'タイムコードなしのテキスト'
  ];
  
  samples.forEach((sample, index) => {
    Logger.log(`サンプル${index + 1}: ${sample}`);
    
    const result = parseTimecodeRange(sample);
    
    if (result) {
      Logger.log(`  ✅ 解析成功`);
      Logger.log(`     イン点: ${result.inPoint}`);
      Logger.log(`     アウト点: ${result.outPoint}`);
      Logger.log(`     文字起こし: "${result.transcription}"`);
      Logger.log(`     文字数: ${result.transcription.length}`);
    } else {
      Logger.log(`  ❌ 解析失敗`);
    }
    Logger.log('');
  });
}

/**
 * 手動で1行ずつ処理するテスト
 */
function manualProcessTest() {
  const sheet = SpreadsheetApp.getActiveSheet();
  
  Logger.log('=== 手動処理テスト ===');
  
  // 2行目のデータをテスト（1行目はヘッダー）
  const testRow = 2;
  const cellValue = sheet.getRange(testRow, 1).getValue();
  
  Logger.log(`テスト対象 (${testRow}行目): "${cellValue}"`);
  Logger.log(`データ型: ${typeof cellValue}`);
  
  if (cellValue && typeof cellValue === 'string') {
    const result = parseTimecodeRange(cellValue);
    
    if (result) {
      Logger.log('✅ 解析成功');
      Logger.log(`イン点: ${result.inPoint}`);
      Logger.log(`アウト点: ${result.outPoint}`);  
      Logger.log(`文字起こし: "${result.transcription}"`);
      
      // 実際にセルに書き込んでテスト
      sheet.getRange(testRow, 4).setValue('テスト文字起こし');
      Logger.log('D列にテスト文字列を書き込みました');
      
    } else {
      Logger.log('❌ 解析失敗');
    }
  } else {
    Logger.log('❌ セルが空または文字列ではありません');
  }
}

/**
 * 問題のあるデータ形式を特定
 */
function identifyDataFormat() {
  const sheet = SpreadsheetApp.getActiveSheet();
  const dataRange = sheet.getDataRange();
  const data = dataRange.getValues();
  
  Logger.log('=== データ形式特定 ===');
  
  for (let i = 0; i < Math.min(data.length, 10); i++) {
    const cellValue = data[i][0];
    
    if (cellValue && typeof cellValue === 'string') {
      Logger.log(`行${i + 1}:`);
      Logger.log(`  値: "${cellValue}"`);
      Logger.log(`  長さ: ${cellValue.length}`);
      
      // 特殊文字チェック
      const hasSquareBrackets = cellValue.includes('[') && cellValue.includes(']');
      const hasTimePattern = /\d{2}:\d{2}:\d{2}:\d{2}/.test(cellValue);
      const hasDash = cellValue.includes('-');
      
      Logger.log(`  角括弧: ${hasSquareBrackets}`);
      Logger.log(`  時間パターン: ${hasTimePattern}`);
      Logger.log(`  ダッシュ: ${hasDash}`);
      
      // 正規表現マッチテスト
      const timePattern = /\[(\d{2}:\d{2}:\d{2}:\d{2})\s*-\s*(\d{2}:\d{2}:\d{2}:\d{2})\]/;
      const match = cellValue.match(timePattern);
      
      if (match) {
        Logger.log(`  ✅ 正規表現マッチ成功`);
        Logger.log(`    イン点: ${match[1]}`);
        Logger.log(`    アウト点: ${match[2]}`);
        
        const transcription = cellValue.replace(timePattern, '').trim();
        Logger.log(`    残りテキスト: "${transcription}"`);
      } else {
        Logger.log(`  ❌ 正規表現マッチ失敗`);
      }
      Logger.log('');
    }
  }
}