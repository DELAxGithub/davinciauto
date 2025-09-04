/**
 * 書き起こし → DaVinciマーカー用CSV変換 GAS
 * 
 * 入力: A列に [タイムコード範囲] テキスト形式
 * 出力: DaVinciマーカー完璧フォーマット
 */

// =====================================================
// 📋 推奨カラム構成（DaVinciマーカー最適化）
// =====================================================
/*
A列: color (話題別色分け)
B列: timecode (In点タイムコード) 
C列: timecode_out (Out点タイムコード)
D列: transcription (書き起こしテキスト)
E列: marker_name (マーカー名 - 自動生成)
F列: note (コメント・要約)
G列: speaker (話者推定)
H列: can_cut (カット可否)
I列: duration_frames (デュレーション)

最終出力: DaVinci用CSV
timecode,marker_name,color,note,duration_frames,speaker,topic,can_cut
*/

/**
 * メイン変換処理
 */
function convertTranscriptionToMarkers() {
  const sheet = SpreadsheetApp.getActiveSheet();
  const data = sheet.getDataRange().getValues();
  
  // 結果格納用配列
  const markers = [];
  
  // ヘッダー追加
  markers.push([
    'color', 'timecode', 'timecode_out', 'transcription', 
    'marker_name', 'note', 'speaker', 'can_cut', 'duration_frames'
  ]);
  
  // データ処理
  for (let i = 0; i < data.length; i++) {
    const cellValue = data[i][0]; // A列の値
    
    if (!cellValue || typeof cellValue !== 'string') continue;
    
    // タイムコード範囲解析
    const timeMatch = cellValue.match(/\[(\d{2}:\d{2}:\d{2}:\d{2})\s*-\s*(\d{2}:\d{2}:\d{2}:\d{2})\]/);
    if (!timeMatch) continue;
    
    const inPoint = timeMatch[1];
    const outPoint = timeMatch[2];
    const transcription = cellValue.replace(/\[.*?\]\s*/, '').trim();
    
    // 基本情報生成
    const markerData = analyzeTranscription(inPoint, outPoint, transcription, i + 1);
    
    markers.push([
      markerData.color,
      markerData.timecode, 
      markerData.timecode_out,
      markerData.transcription,
      markerData.marker_name,
      markerData.note,
      markerData.speaker,
      markerData.can_cut,
      markerData.duration_frames
    ]);
  }
  
  // 結果を新しいシートに出力
  createResultSheet(markers);
  
  Logger.log(`変換完了: ${markers.length - 1} 個のマーカーを生成`);
}

/**
 * 書き起こし内容の分析・分類
 */
function analyzeTranscription(inPoint, outPoint, transcription, index) {
  // デュレーション計算（フレーム数）
  const durationFrames = calculateDurationFrames(inPoint, outPoint);
  
  // 話者推定
  const speaker = estimateSpeaker(transcription);
  
  // 話題分類と色決定
  const topicAnalysis = classifyTopic(transcription);
  
  // マーカー名生成
  const markerName = generateMarkerName(transcription, index);
  
  // 要約・コメント生成
  const note = generateNote(transcription);
  
  // カット可否判定
  const canCut = determineCanCut(transcription, topicAnalysis);
  
  return {
    color: topicAnalysis.color,
    timecode: inPoint,
    timecode_out: outPoint, 
    transcription: transcription,
    marker_name: markerName,
    note: note,
    speaker: speaker,
    can_cut: canCut,
    duration_frames: durationFrames
  };
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

/**
 * 話者推定
 */
function estimateSpeaker(text) {
  // 簡易的な話者推定ロジック
  if (text.includes('NHK') || text.includes('番組') || text.includes('紹介')) {
    return 'ナレーター';
  } else if (text.includes('です') || text.includes('ます')) {
    return '出演者';
  } else if (text.includes('CM') || text.includes('コマーシャル')) {
    return 'CM';
  }
  return '不明';
}

/**
 * 話題分類・色決定（DaVinci実際の色名に対応）
 */
function classifyTopic(text) {
  // キーワードベース分類 - DaVinci実色名使用
  if (text.includes('CM') || text.includes('コマーシャル') || text.includes('広告')) {
    return { color: 'lemon', topic: 'コマーシャル' };  // 黄色系
  } else if (text.includes('NHK') || text.includes('番組') || text.includes('紹介') || text.includes('開始')) {
    return { color: 'cyan', topic: 'オープニング' };  // 水色系
  } else if (text.includes('料理') || text.includes('レシピ') || text.includes('作り方')) {
    return { color: 'mint', topic: '料理・レシピ' };  // 緑系
  } else if (text.includes('花') || text.includes('ガーデン') || text.includes('植物')) {
    return { color: 'mint', topic: '園芸・花' };  // 緑系
  } else if (text.includes('重要') || text.includes('大切') || text.includes('ポイント') || text.includes('キーポイント')) {
    return { color: 'rose', topic: '重要内容' };  // 赤系
  } else if (text.includes('対談') || text.includes('インタビュー') || text.includes('討論')) {
    return { color: 'lavender', topic: '対談・討論' };  // 紫系
  } else if (text.includes('まとめ') || text.includes('終了') || text.includes('エンディング')) {
    return { color: 'sky', topic: 'まとめ・終了' };  // 空色系
  }
  
  // デフォルト
  return { color: 'cyan', topic: '一般' };
}

/**
 * マーカー名生成
 */
function generateMarkerName(text, index) {
  // 最初の10文字 + 連番
  const shortText = text.substring(0, 10).replace(/[。、]/g, '');
  return `${String(index).padStart(3, '0')}_${shortText}`;
}

/**
 * ノート・要約生成
 */
function generateNote(text) {
  // 30文字で要約
  if (text.length <= 30) {
    return text;
  }
  return text.substring(0, 27) + '...';
}

/**
 * カット可否判定
 */
function determineCanCut(text, topicAnalysis) {
  // 重要コンテンツは保護
  if (topicAnalysis.color === 'red') {
    return 'false';
  }
  // CMはカット可能
  if (topicAnalysis.topic === 'コマーシャル') {
    return 'true';
  }
  // 短い発言はカット可能
  if (text.length < 20) {
    return 'true';
  }
  
  // デフォルトは保護
  return 'false';
}

/**
 * 結果シート作成
 */
function createResultSheet(markers) {
  const spreadsheet = SpreadsheetApp.getActiveSpreadsheet();
  
  // 既存の結果シートを削除
  const existingSheet = spreadsheet.getSheetByName('DaVinciマーカー');
  if (existingSheet) {
    spreadsheet.deleteSheet(existingSheet);
  }
  
  // 新しい結果シート作成
  const resultSheet = spreadsheet.insertSheet('DaVinciマーカー');
  
  // データ書き込み
  if (markers.length > 0) {
    const range = resultSheet.getRange(1, 1, markers.length, markers[0].length);
    range.setValues(markers);
    
    // ヘッダー行の書式設定
    const headerRange = resultSheet.getRange(1, 1, 1, markers[0].length);
    headerRange.setFontWeight('bold');
    headerRange.setBackground('#E8F4F8');
  }
  
  // カラム幅自動調整
  resultSheet.autoResizeColumns(1, markers[0].length);
  
  Logger.log('結果シート "DaVinciマーカー" を作成しました');
}

/**
 * DaVinci用最終CSV生成
 */
function generateDaVinciCSV() {
  const sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName('DaVinciマーカー');
  if (!sheet) {
    Logger.log('エラー: DaVinciマーカーシートが見つかりません');
    return;
  }
  
  const data = sheet.getDataRange().getValues();
  
  // DaVinci用フォーマットに変換
  const csvData = [];
  csvData.push(['timecode', 'marker_name', 'color', 'note', 'duration_frames', 'speaker', 'topic', 'can_cut']);
  
  for (let i = 1; i < data.length; i++) {
    const row = data[i];
    csvData.push([
      row[1], // timecode (B列)
      row[4], // marker_name (E列) 
      row[0], // color (A列)
      row[5], // note (F列)
      row[8], // duration_frames (I列)
      row[6], // speaker (G列)
      row[0], // topic (色から推定)
      row[7]  // can_cut (H列)
    ]);
  }
  
  // CSV文字列生成
  const csvContent = csvData.map(row => 
    row.map(cell => `"${cell}"`).join(',')
  ).join('\n');
  
  // 新しいシートに出力
  const csvSheet = SpreadsheetApp.getActiveSpreadsheet().insertSheet('DaVinci_CSV');
  csvSheet.getRange(1, 1).setValue(csvContent);
  
  Logger.log('DaVinci用CSVを生成しました');
}

// =====================================================
// 🎨 スマート色選択システム
// =====================================================

/**
 * DaVinci色対応のデータ検証とUI設定
 */
function setupSmartColorSystem() {
  const sheet = SpreadsheetApp.getActiveSheet();
  
  // DaVinci色リスト（実際のパレット対応）
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
  
  // 対応する背景色（Hex値）
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
  
  // A列の範囲取得（データがある行まで）
  const dataRange = sheet.getDataRange();
  const numRows = dataRange.getNumRows();
  
  if (numRows === 0) {
    Logger.log('データがありません');
    return;
  }
  
  // A列にデータ検証（プルダウン）を設定
  const colorRange = sheet.getRange(1, 1, numRows, 1);
  const rule = SpreadsheetApp.newDataValidation()
    .requireValueInList(davinciColors)
    .setAllowInvalid(false)
    .setHelpText('DaVinci Resolve対応色を選択してください')
    .build();
    
  colorRange.setDataValidation(rule);
  
  // 条件付き書式を設定（色選択に応じてセル背景色変更）
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
  
  Logger.log('✅ スマート色選択システム設定完了');
  Logger.log(`   📋 ${davinciColors.length}色のプルダウン + 背景色連動`);
}

/**
 * 自動色分類（既存の書き起こしテキスト用）
 */
function autoClassifyColors() {
  const sheet = SpreadsheetApp.getActiveSheet();
  const data = sheet.getDataRange().getValues();
  
  let updateCount = 0;
  
  for (let i = 0; i < data.length; i++) {
    const cellValue = data[i][0];
    
    if (!cellValue || typeof cellValue !== 'string') continue;
    
    // 書き起こしテキストから自動分類
    const transcription = cellValue.replace(/\[.*?\]\s*/, '').trim();
    const topicAnalysis = classifyTopic(transcription);
    
    // A列に色を自動設定
    sheet.getRange(i + 1, 1).setValue(topicAnalysis.color);
    updateCount++;
  }
  
  Logger.log(`✅ 自動色分類完了: ${updateCount}行を更新`);
}

// =====================================================
// 🚀 実行用関数
// =====================================================

/**
 * 初期セットアップ（色システム + 変換）
 */
function setupAndConvert() {
  Logger.log('=== スマート色選択 + 変換システム初期化 ===');
  
  try {
    // Step 1: 色選択システム設定
    setupSmartColorSystem();
    
    // Step 2: 既存データの自動色分類
    autoClassifyColors();
    
    Logger.log('=== セットアップ完了！A列で色を選択してから変換実行してください ===');
    
  } catch (error) {
    Logger.log(`エラー: ${error.message}`);
  }
}

/**
 * 変換実行（色選択済み前提）
 */
function executeConversion() {
  Logger.log('=== 書き起こし → DaVinciマーカー変換開始 ===');
  
  try {
    // Step 1: 基本変換（A列の色を使用）
    convertTranscriptionWithColors();
    
    // Step 2: DaVinci用CSV生成
    generateDaVinciCSV();
    
    Logger.log('=== 変換完了！DaVinci_CSVシートを確認してください ===');
    
  } catch (error) {
    Logger.log(`エラー: ${error.message}`);
  }
}

/**
 * ワンクリック実行（従来版）
 */
function executeAll() {
  Logger.log('=== 書き起こし → DaVinciマーカー変換開始 ===');
  
  try {
    // Step 1: 基本変換
    convertTranscriptionToMarkers();
    
    // Step 2: DaVinci用CSV生成
    generateDaVinciCSV();
    
    Logger.log('=== 変換完了！DaVinci_CSVシートを確認してください ===');
    
  } catch (error) {
    Logger.log(`エラー: ${error.message}`);
  }
}

/**
 * 色選択対応版の変換処理
 */
function convertTranscriptionWithColors() {
  const sheet = SpreadsheetApp.getActiveSheet();
  const data = sheet.getDataRange().getValues();
  
  // 結果格納用配列
  const markers = [];
  
  // ヘッダー追加
  markers.push([
    'color', 'timecode', 'timecode_out', 'transcription', 
    'marker_name', 'note', 'speaker', 'can_cut', 'duration_frames'
  ]);
  
  // データ処理
  for (let i = 0; i < data.length; i++) {
    const colorCell = data[i][0]; // A列（色指定）
    const transcriptionCell = data[i][1] || data[i][0]; // B列または統合セル
    
    if (!transcriptionCell || typeof transcriptionCell !== 'string') continue;
    
    // タイムコード範囲解析
    const timeMatch = transcriptionCell.match(/\[(\d{2}:\d{2}:\d{2}:\d{2})\s*-\s*(\d{2}:\d{2}:\d{2}:\d{2})\]/);
    if (!timeMatch) continue;
    
    const inPoint = timeMatch[1];
    const outPoint = timeMatch[2];
    const transcription = transcriptionCell.replace(/\[.*?\]\s*/, '').trim();
    
    // 色指定確認（A列に色があればそれを使用、なければ自動分類）
    let selectedColor = colorCell;
    if (!selectedColor || selectedColor === transcriptionCell) {
      const topicAnalysis = classifyTopic(transcription);
      selectedColor = topicAnalysis.color;
    }
    
    // マーカーデータ生成
    const markerData = analyzeTranscriptionWithColor(
      inPoint, outPoint, transcription, selectedColor, i + 1
    );
    
    markers.push([
      markerData.color,
      markerData.timecode, 
      markerData.timecode_out,
      markerData.transcription,
      markerData.marker_name,
      markerData.note,
      markerData.speaker,
      markerData.can_cut,
      markerData.duration_frames
    ]);
  }
  
  // 結果を新しいシートに出力
  createResultSheet(markers);
  
  Logger.log(`変換完了: ${markers.length - 1} 個のマーカーを生成`);
}

/**
 * 色指定対応版の分析処理
 */
function analyzeTranscriptionWithColor(inPoint, outPoint, transcription, selectedColor, index) {
  // デュレーション計算
  const durationFrames = calculateDurationFrames(inPoint, outPoint);
  
  // 話者推定
  const speaker = estimateSpeaker(transcription);
  
  // マーカー名生成
  const markerName = generateMarkerName(transcription, index);
  
  // 要約生成
  const note = generateNote(transcription);
  
  // カット可否判定（色ベースも考慮）
  const canCut = determineCanCutByColor(transcription, selectedColor);
  
  return {
    color: selectedColor,
    timecode: inPoint,
    timecode_out: outPoint, 
    transcription: transcription,
    marker_name: markerName,
    note: note,
    speaker: speaker,
    can_cut: canCut,
    duration_frames: durationFrames
  };
}

/**
 * 色ベースのカット可否判定
 */
function determineCanCutByColor(text, color) {
  // 色別カット可否ルール
  if (color === 'rose') { // 重要内容
    return 'false';
  } else if (color === 'lemon') { // コマーシャル
    return 'true';
  } else if (color === 'cyan' && text.length < 30) { // 短いオープニング
    return 'true';
  }
  
  // デフォルト判定
  return text.length < 20 ? 'true' : 'false';
}