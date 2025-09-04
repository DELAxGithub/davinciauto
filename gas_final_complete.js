/**
 * 最終版: DaVinci Resolve マーカー生成システム
 * Google Apps Script - カスタムメニュー付き完全版
 */

/**
 * メニュー作成（スプレッドシート開いた時に自動実行）
 */
function onOpen() {
  const ui = SpreadsheetApp.getUi();
  
  ui.createMenu('🎬 DaVinci マーカー生成')
    .addItem('📝 Step 1: データ解析・整形', 'executeStep1')
    .addSeparator()
    .addItem('🎨 Step 2: 色分け選択', 'executeStep2')
    .addSeparator()
    .addItem('🎯 Step 3: マーカーCSV生成', 'executeStep3')
    .addSeparator()
    .addItem('📊 データ統計表示', 'showDataStatistics')
    .addItem('🔧 全データリセット', 'resetAllData')
    .addToUi();
}

// =============================================================================
// Step 1: データ解析・整形
// =============================================================================

/**
 * Step 1: ペアデータ処理メイン関数
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
 * Step 1 実行関数
 */
function executeStep1() {
  Logger.log('🚀 Step 1: データ解析・整形 実行開始');
  
  try {
    const result = parseTranscriptionPairs();
    
    // ユーザー通知
    const ui = SpreadsheetApp.getUi();
    ui.alert(
      'Step 1 完了',
      `✅ ${result.success}個のタイムコード+文字起こしペアを処理しました\n` +
      `⚠️ ${result.skipped}行をスキップしました\n\n` +
      `次: Step 2で色分け選択を行ってください`,
      ui.ButtonSet.OK
    );
    
    Logger.log('🎉 Step 1 完了！');
    return result;
    
  } catch (error) {
    Logger.log(`💥 実行エラー: ${error.message}`);
    SpreadsheetApp.getUi().alert('エラー', `Step 1でエラーが発生しました:\n${error.message}`, SpreadsheetApp.getUi().ButtonSet.OK);
    return null;
  }
}

// =============================================================================
// Step 2: 色分け選択
// =============================================================================

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
    return { error: 'Step 1を先に実行してください' };
  }
  
  // D列のヘッダーを追加
  sheet.getRange(1, 4).setValue('色選択');
  
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
  
  // 各行の文字起こしを分析して色を自動推定（デフォルトは空白）
  for (let i = 1; i < data.length; i++) {  // 1行目はヘッダーなので除く
    const transcription = data[i][2]; // C列の文字起こし
    
    if (transcription && typeof transcription === 'string') {
      // 話題分析（自動推定）
      const topicAnalysis = classifyTopic(transcription);
      
      // D列は空白のままにして、ユーザーが手動選択できるようにする
      sheet.getRange(i + 1, 4).setValue(''); // 空白
      
      processedCount++;
      Logger.log(`行${i + 1}: "${transcription.substring(0, 20)}..." → 推定: ${topicAnalysis.color} (${topicAnalysis.topic})`);
    }
  }
  
  // D列にプルダウン設定
  const colorRange = sheet.getRange(2, 4, data.length - 1, 1);
  const rule = SpreadsheetApp.newDataValidation()
    .requireValueInList(davinciColors)
    .setAllowInvalid(false)
    .setHelpText('使用したいマーカーの色を選択（空白=使わない）')
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
  Logger.log(`✅ ${processedCount}行に色選択を追加`);
  Logger.log(`📊 結果:`);
  Logger.log(`   A列: イン点`);
  Logger.log(`   B列: アウト点`);
  Logger.log(`   C列: 文字起こし`);
  Logger.log(`   D列: 色選択（プルダウン + 背景色連動）`);
  
  return { processed: processedCount };
}

/**
 * 話題分類ロジック（自動推定用）
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
 * Step 2 実行関数
 */
function executeStep2() {
  Logger.log('🚀 Step 2: 色分け選択 実行開始');
  
  try {
    const result = addColorClassification();
    
    if (result.error) {
      SpreadsheetApp.getUi().alert('エラー', result.error, SpreadsheetApp.getUi().ButtonSet.OK);
      return null;
    }
    
    // 統計表示
    const colorStats = showColorStats();
    
    // ユーザー通知
    const ui = SpreadsheetApp.getUi();
    ui.alert(
      'Step 2 完了',
      `✅ ${result.processed}行に色選択プルダウンを追加しました\n\n` +
      `🎨 使用方法:\n` +
      `・D列で使いたいマーカーの色を選択\n` +
      `・空白のままにすると使わない\n` +
      `・背景色が自動で変わります\n\n` +
      `次: 色を選択してからStep 3を実行してください`,
      ui.ButtonSet.OK
    );
    
    Logger.log('🎉 Step 2 完了！');
    return result;
    
  } catch (error) {
    Logger.log(`💥 実行エラー: ${error.message}`);
    SpreadsheetApp.getUi().alert('エラー', `Step 2でエラーが発生しました:\n${error.message}`, SpreadsheetApp.getUi().ButtonSet.OK);
    return null;
  }
}

// =============================================================================
// Step 3: マーカーCSV生成（同一色区間のデュレーションマーカー）
// =============================================================================

/**
 * 同一色区間のデュレーションマーカー生成
 */
function generateDurationMarkers() {
  const sheet = SpreadsheetApp.getActiveSheet();
  
  Logger.log('=== Step 3: 同一色区間マーカー生成開始 ===');
  
  // 現在のデータ取得
  const dataRange = sheet.getDataRange();
  const data = dataRange.getValues();
  
  if (data.length <= 1) {
    Logger.log('❌ データが不足しています。');
    return { error: 'Step 1, 2を先に実行してください' };
  }
  
  // 結果格納配列
  const csvData = [];
  
  // アウト点対応ヘッダー
  csvData.push(['timecode_in', 'timecode_out', 'marker_name', 'color', 'note', 'duration_frames', 'keywords']);
  
  // 同一色区間を検出してマーカー生成
  const colorRegions = detectColorRegions(data);
  
  let markerCount = 0;
  
  colorRegions.forEach((region, index) => {
    try {
      // マーカーデータ作成
      const markerData = createDurationMarker(region, index + 1);
      
      csvData.push([
        markerData.timecode_in,
        markerData.timecode_out,
        markerData.marker_name,
        markerData.color,
        markerData.note,
        markerData.duration_frames,
        markerData.keywords
      ]);
      
      markerCount++;
      Logger.log(`✅ 区間${index + 1}: ${region.color} (行${region.startRow}-${region.endRow}) - ${markerData.marker_name}`);
      
    } catch (error) {
      Logger.log(`❌ 区間${index + 1}: エラー - ${error.message}`);
    }
  });
  
  // 新しいシートに結果出力
  createCSVSheet(csvData, 'DaVinciMarkers');
  
  // 結果レポート
  Logger.log('');
  Logger.log('=== Step 3 完了 ===');
  Logger.log(`✅ 生成マーカー: ${markerCount}個`);
  Logger.log(`📊 同一色区間をデュレーションマーカーに変換完了`);
  
  return { generated: markerCount, regions: colorRegions.length };
}

/**
 * 同一色区間の検出
 */
function detectColorRegions(data) {
  const regions = [];
  let currentRegion = null;
  
  Logger.log('=== 色区間検出開始 ===');
  
  // データ行を走査（1行目はヘッダーなので除く）
  for (let i = 1; i < data.length; i++) {
    const inPoint = data[i][0];      // A列: イン点
    const outPoint = data[i][1];     // B列: アウト点
    const transcription = data[i][2]; // C列: 文字起こし
    const color = data[i][3];        // D列: カラー
    
    // 色が設定されていない行はスキップ
    if (!color || color.toString().trim() === '') {
      // 現在の区間があれば終了
      if (currentRegion) {
        regions.push(currentRegion);
        Logger.log(`区間終了: ${currentRegion.color} (行${currentRegion.startRow}-${currentRegion.endRow})`);
        currentRegion = null;
      }
      continue;
    }
    
    // 新しい区間の開始または継続の判定
    if (!currentRegion || currentRegion.color !== color) {
      // 前の区間があれば保存
      if (currentRegion) {
        regions.push(currentRegion);
        Logger.log(`区間終了: ${currentRegion.color} (行${currentRegion.startRow}-${currentRegion.endRow})`);
      }
      
      // 新しい区間開始
      currentRegion = {
        color: color,
        startRow: i + 1,  // 表示用（1始まり）
        endRow: i + 1,
        startTime: inPoint,
        endTime: outPoint,
        transcriptions: [transcription]
      };
      
      Logger.log(`新区間開始: ${color} (行${i + 1})`);
      
    } else {
      // 同じ色の継続
      currentRegion.endRow = i + 1;
      currentRegion.endTime = outPoint;
      currentRegion.transcriptions.push(transcription);
    }
  }
  
  // 最後の区間があれば保存
  if (currentRegion) {
    regions.push(currentRegion);
    Logger.log(`区間終了: ${currentRegion.color} (行${currentRegion.startRow}-${currentRegion.endRow})`);
  }
  
  Logger.log(`=== 検出完了: ${regions.length}個の色区間 ===`);
  
  return regions;
}

/**
 * デュレーションマーカーデータ作成
 */
function createDurationMarker(region, markerIndex) {
  // デュレーション計算（区間全体）
  const durationFrames = calculateDurationFrames(region.startTime, region.endTime);
  
  // マーカー名生成
  const markerName = `${String(markerIndex).padStart(3, '0')}_${region.color}_区間`;
  
  // コメント（区間の文字起こし要約）
  const allText = region.transcriptions.join(' ');
  const note = allText.length > 80 ? allText.substring(0, 77) + '...' : allText;
  
  // キーワード抽出（区間全体から）
  const keywords = extractKeywords(allText);
  
  return {
    timecode_in: region.startTime,
    timecode_out: region.endTime,
    marker_name: markerName,
    color: region.color,
    note: note,
    duration_frames: durationFrames,
    keywords: keywords
  };
}

/**
 * デュレーション計算
 */
function calculateDurationFrames(inPoint, outPoint) {
  try {
    const [inH, inM, inS, inF] = inPoint.toString().split(':').map(Number);
    const [outH, outM, outS, outF] = outPoint.toString().split(':').map(Number);
    
    const inTotalFrames = (inH * 3600 + inM * 60 + inS) * 25 + inF;
    const outTotalFrames = (outH * 3600 + outM * 60 + outS) * 25 + outF;
    
    return Math.max(outTotalFrames - inTotalFrames, 1);
  } catch (error) {
    Logger.log(`⚠️  デュレーション計算エラー: ${error.message}`);
    return 25; // デフォルト1秒
  }
}

/**
 * キーワード抽出（簡易版）
 */
function extractKeywords(text) {
  const textStr = text.toString();
  
  // 基本的なキーワードパターン
  const keywordPatterns = [
    { pattern: /料理|レシピ|作り方|調理|食材/, keyword: '料理' },
    { pattern: /花|植物|ガーデン|園芸/, keyword: '園芸' },
    { pattern: /NHK|番組|放送|テレビ/, keyword: '番組' },
    { pattern: /CM|コマーシャル|広告/, keyword: 'CM' },
    { pattern: /重要|大切|ポイント/, keyword: '重要' },
    { pattern: /時間|分|今|今日/, keyword: '時間' },
    { pattern: /場所|ここ|そこ/, keyword: '場所' },
    { pattern: /良い|悪い|美味し|楽し/, keyword: '評価' },
    { pattern: /さん|先生|お客/, keyword: '人物' }
  ];
  
  const foundKeywords = [];
  
  for (const { pattern, keyword } of keywordPatterns) {
    if (pattern.test(textStr)) {
      foundKeywords.push(keyword);
    }
  }
  
  const uniqueKeywords = [...new Set(foundKeywords)].slice(0, 3);
  
  if (uniqueKeywords.length === 0) {
    return textStr.length < 30 ? '短文' : '一般';
  }
  
  return uniqueKeywords.join(', ');
}

/**
 * CSV専用シート作成
 */
function createCSVSheet(csvData, sheetName) {
  const spreadsheet = SpreadsheetApp.getActiveSpreadsheet();
  
  // 既存シート削除
  const existingSheet = spreadsheet.getSheetByName(sheetName);
  if (existingSheet) {
    spreadsheet.deleteSheet(existingSheet);
  }
  
  // 新しいシート作成
  const csvSheet = spreadsheet.insertSheet(sheetName);
  
  // データ書き込み
  if (csvData.length > 0) {
    const range = csvSheet.getRange(1, 1, csvData.length, csvData[0].length);
    range.setValues(csvData);
    
    // ヘッダー書式
    const headerRange = csvSheet.getRange(1, 1, 1, csvData[0].length);
    headerRange.setFontWeight('bold');
    headerRange.setBackground('#E8F4F8');
    
    // カラム幅調整
    csvSheet.autoResizeColumns(1, csvData[0].length);
  }
  
  Logger.log(`✅ "${sheetName}"シートを作成しました`);
}

/**
 * Step 3 実行関数
 */
function executeStep3() {
  Logger.log('🚀 Step 3: マーカーCSV生成 実行開始');
  
  try {
    const result = generateDurationMarkers();
    
    if (result.error) {
      SpreadsheetApp.getUi().alert('エラー', result.error, SpreadsheetApp.getUi().ButtonSet.OK);
      return null;
    }
    
    // ユーザー通知
    const ui = SpreadsheetApp.getUi();
    ui.alert(
      'Step 3 完了',
      `✅ ${result.generated}個のデュレーションマーカーを生成しました\n\n` +
      `📊 結果:\n` +
      `・「DaVinciMarkers」シートが作成されました\n` +
      `・同一色区間がデュレーションマーカーに変換されています\n\n` +
      `🎬 次のステップ:\n` +
      `1. 「DaVinciMarkers」シートをCSVダウンロード\n` +
      `2. DaVinciのコンソールで run_csv() 実行\n` +
      `3. 自動でマーカー配置完了！`,
      ui.ButtonSet.OK
    );
    
    Logger.log('🎉 Step 3 完了！');
    return result;
    
  } catch (error) {
    Logger.log(`💥 実行エラー: ${error.message}`);
    SpreadsheetApp.getUi().alert('エラー', `Step 3でエラーが発生しました:\n${error.message}`, SpreadsheetApp.getUi().ButtonSet.OK);
    return null;
  }
}

// =============================================================================
// 統計・ユーティリティ機能
// =============================================================================

/**
 * 色分け統計表示
 */
function showColorStats() {
  const sheet = SpreadsheetApp.getActiveSheet();
  const dataRange = sheet.getDataRange();
  const data = dataRange.getValues();
  
  Logger.log('=== 色分け統計 ===');
  
  const colorCounts = {};
  let totalRows = 0;
  
  // D列（色）の統計
  for (let i = 1; i < data.length; i++) {
    totalRows++;
    const color = data[i][3];
    if (color && color.toString().trim() !== '') {
      colorCounts[color] = (colorCounts[color] || 0) + 1;
    } else {
      colorCounts['未選択'] = (colorCounts['未選択'] || 0) + 1;
    }
  }
  
  // 統計表示
  Object.entries(colorCounts).forEach(([color, count]) => {
    Logger.log(`${color}: ${count}個`);
  });
  
  Logger.log(`合計: ${totalRows}個`);
  
  return colorCounts;
}

/**
 * データ統計表示
 */
function showDataStatistics() {
  try {
    const colorStats = showColorStats();
    const totalColors = Object.values(colorStats).reduce((a, b) => a + b, 0);
    const selectedColors = totalColors - (colorStats['未選択'] || 0);
    
    let statsText = '📊 現在のデータ統計:\n\n';
    
    Object.entries(colorStats).forEach(([color, count]) => {
      const percentage = totalColors > 0 ? Math.round((count / totalColors) * 100) : 0;
      statsText += `${color}: ${count}個 (${percentage}%)\n`;
    });
    
    statsText += `\n合計: ${totalColors}個\n`;
    statsText += `色選択済み: ${selectedColors}個\n`;
    statsText += `選択率: ${totalColors > 0 ? Math.round((selectedColors / totalColors) * 100) : 0}%`;
    
    SpreadsheetApp.getUi().alert('データ統計', statsText, SpreadsheetApp.getUi().ButtonSet.OK);
    
  } catch (error) {
    SpreadsheetApp.getUi().alert('エラー', 'データ統計の表示でエラーが発生しました', SpreadsheetApp.getUi().ButtonSet.OK);
  }
}

/**
 * 全データリセット
 */
function resetAllData() {
  const ui = SpreadsheetApp.getUi();
  const response = ui.alert(
    '全データリセット', 
    '現在のシートを完全にクリアして最初からやり直しますか？\n（この操作は元に戻せません）',
    ui.ButtonSet.YES_NO
  );
  
  if (response === ui.Button.YES) {
    const sheet = SpreadsheetApp.getActiveSheet();
    sheet.clear();
    sheet.clearConditionalFormatRules();
    
    // DaVinciマーカーシートも削除
    const spreadsheet = SpreadsheetApp.getActiveSpreadsheet();
    const markerSheet = spreadsheet.getSheetByName('DaVinciMarkers');
    if (markerSheet) {
      spreadsheet.deleteSheet(markerSheet);
    }
    
    ui.alert('リセット完了', '全データをリセットしました。\n元の文字起こしデータを貼り付けてStep 1から開始してください。', ui.ButtonSet.OK);
    Logger.log('🔄 全データリセット完了');
  }
}

// =============================================================================
// 初期化メッセージ
// =============================================================================

Logger.log('🎬 DaVinci Resolve マーカー生成システム - 最終版');
Logger.log('メニューから「🎬 DaVinci マーカー生成」を選択してStep 1から順番に実行してください');