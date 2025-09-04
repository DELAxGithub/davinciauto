/**
 * Step 3 正しい版: 同一色区間のデュレーションマーカー生成
 * D列=カラー、E列=コメント、F列=キーワード
 */

/**
 * 同一色区間のデュレーションマーカー生成
 */
function generateDurationMarkers() {
  const sheet = SpreadsheetApp.getActiveSheet();
  
  Logger.log('=== Step 3 正しい版: 同一色区間マーカー生成開始 ===');
  
  // 現在のデータ取得
  const dataRange = sheet.getDataRange();
  const data = dataRange.getValues();
  
  if (data.length <= 1) {
    Logger.log('❌ データが不足しています。');
    return;
  }
  
  // 結果格納配列
  const csvData = [];
  
  // シンプルなヘッダー
  csvData.push(['timecode', 'marker_name', 'color', 'note', 'duration_frames', 'keywords']);
  
  // 同一色区間を検出してマーカー生成
  const colorRegions = detectColorRegions(data);
  
  let markerCount = 0;
  
  colorRegions.forEach((region, index) => {
    try {
      // マーカーデータ作成
      const markerData = createDurationMarker(region, index + 1);
      
      csvData.push([
        markerData.timecode,
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
  createSimpleCSVSheet(csvData);
  
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
    timecode: region.startTime,
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
 * シンプルなCSVシート作成
 */
function createSimpleCSVSheet(csvData) {
  const spreadsheet = SpreadsheetApp.getActiveSpreadsheet();
  
  // 既存シート削除
  const existingSheet = spreadsheet.getSheetByName('DaVinci区間マーカー');
  if (existingSheet) {
    spreadsheet.deleteSheet(existingSheet);
  }
  
  // 新しいシート作成
  const csvSheet = spreadsheet.insertSheet('DaVinci区間マーカー');
  
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
  
  Logger.log('✅ "DaVinci区間マーカー"シートを作成しました');
}

/**
 * ワンクリック実行 - Step 3 正しい版
 */
function executeStep3Correct() {
  Logger.log('🚀 Step 3 正しい版: 区間マーカー生成実行開始');
  
  try {
    const result = generateDurationMarkers();
    
    Logger.log('');
    Logger.log('🎉 Step 3 正しい版完了！');
    Logger.log('"DaVinci区間マーカー"シートが作成されました');
    Logger.log('同一色区間がデュレーションマーカーに変換されています');
    
    return result;
    
  } catch (error) {
    Logger.log(`💥 実行エラー: ${error.message}`);
    return null;
  }
}