/**
 * Step 3: DaVinci用CSV生成機能
 * 色分けされたデータからDaVinci Resolveで読み込める形式のCSVを生成
 */

/**
 * DaVinci用CSV生成メイン関数
 */
function generateDaVinciCSV() {
  const sheet = SpreadsheetApp.getActiveSheet();
  
  Logger.log('=== Step 3: DaVinci用CSV生成開始 ===');
  
  // 現在のデータ取得
  const dataRange = sheet.getDataRange();
  const data = dataRange.getValues();
  
  if (data.length <= 1) {
    Logger.log('❌ データが不足しています。Step 1, 2を先に実行してください。');
    return;
  }
  
  // 結果格納配列（DaVinciフォーマット）
  const csvData = [];
  
  // DaVinci用ヘッダー
  csvData.push(['timecode', 'marker_name', 'color', 'note', 'duration_frames', 'speaker', 'topic', 'can_cut', 'keywords']);
  
  let markerCount = 0;
  let skippedCount = 0;
  
  // 各行を処理
  for (let i = 1; i < data.length; i++) {
    const inPoint = data[i][0];      // A列: イン点
    const outPoint = data[i][1];     // B列: アウト点  
    const transcription = data[i][2]; // C列: 文字起こし
    const selectedColor = data[i][3]; // D列: 話題色
    
    // 必須データチェック
    if (!inPoint || !outPoint || !transcription) {
      Logger.log(`⚠️  行${i + 1}: 必須データ不足 - スキップ`);
      skippedCount++;
      continue;
    }
    
    // 色が設定されていない場合はスキップ（使わない判定）
    if (!selectedColor || selectedColor.toString().trim() === '') {
      Logger.log(`⚠️  行${i + 1}: 色未設定 - スキップ`);
      skippedCount++;
      continue;
    }
    
    try {
      // マーカーデータ生成
      const markerData = createMarkerData(
        inPoint, outPoint, transcription, selectedColor, markerCount + 1
      );
      
      csvData.push([
        markerData.timecode,
        markerData.marker_name,
        markerData.color,
        markerData.note,
        markerData.duration_frames,
        markerData.speaker,
        markerData.topic,
        markerData.can_cut,
        markerData.keywords
      ]);
      
      markerCount++;
      Logger.log(`✅ 行${i + 1}: マーカー生成 - ${markerData.marker_name}`);
      
    } catch (error) {
      Logger.log(`❌ 行${i + 1}: 処理エラー - ${error.message}`);
      skippedCount++;
    }
  }
  
  // 新しいシートに結果出力
  createCSVSheet(csvData);
  
  // 結果レポート
  Logger.log('');
  Logger.log('=== Step 3 完了 ===');
  Logger.log(`✅ 生成マーカー: ${markerCount}個`);
  Logger.log(`⚠️  スキップ: ${skippedCount}個`);
  Logger.log(`📊 CSV生成完了: "DaVinci用CSV"シートを確認`);
  
  return { 
    generated: markerCount, 
    skipped: skippedCount,
    total: markerCount + skippedCount 
  };
}

/**
 * マーカーデータ作成
 */
function createMarkerData(inPoint, outPoint, transcription, selectedColor, markerIndex) {
  // デュレーション計算（25fps基準）
  const durationFrames = calculateDurationFrames(inPoint, outPoint);
  
  // マーカー名生成（連番 + 内容）
  const cleanText = transcription.toString().replace(/[^\w\s\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FAF]/g, '');
  const shortText = cleanText.substring(0, 15);
  const markerName = `${String(markerIndex).padStart(3, '0')}_${shortText}`;
  
  // ノート（要約版）
  const note = transcription.length > 50 ? 
    transcription.substring(0, 47) + '...' : 
    transcription;
  
  // 話者推定（簡易版）
  const speaker = estimateSpeaker(transcription);
  
  // 話題判定（色から）
  const topic = getTopicFromColor(selectedColor);
  
  // カット可否判定（重要色は保護）
  const canCut = (selectedColor === 'rose') ? 'false' : 'true';
  
  // キーワード抽出
  const keywords = extractKeywords(transcription);
  
  return {
    timecode: inPoint,
    marker_name: markerName,
    color: selectedColor,
    note: note,
    duration_frames: durationFrames,
    speaker: speaker,
    topic: topic,
    can_cut: canCut,
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
 * 話者推定
 */
function estimateSpeaker(text) {
  const textStr = text.toString();
  
  if (textStr.includes('NHK') || textStr.includes('番組') || textStr.includes('紹介')) {
    return 'ナレーター';
  } else if (textStr.includes('ありがとう') || textStr.includes('そうですね')) {
    return 'ゲスト';
  } else if (textStr.length < 20) {
    return '相槌';
  }
  
  return '出演者';
}

/**
 * 色から話題を判定
 */
function getTopicFromColor(color) {
  const colorTopicMap = {
    'cyan': 'オープニング',
    'rose': '重要内容',
    'mint': '料理・園芸',
    'lemon': 'コマーシャル',
    'lavender': '対談・討論',
    'sky': 'まとめ・天気',
    'sand': '短いコメント',
    'cream': '一般'
  };
  
  return colorTopicMap[color] || '一般';
}

/**
 * キーワード抽出
 */
function extractKeywords(text) {
  const textStr = text.toString();
  
  // キーワードリスト（優先度順）
  const keywordPatterns = [
    // 料理関連
    { pattern: /料理|レシピ|作り方|調理|食材|味付け|煮込み|炒め|茹で|焼く/, keyword: '料理' },
    
    // 園芸・花関連  
    { pattern: /花|植物|ガーデン|園芸|栽培|種|肥料|水やり|剪定/, keyword: '園芸' },
    
    // 番組・メディア関連
    { pattern: /NHK|番組|放送|テレビ|ラジオ|紹介|企画/, keyword: '番組' },
    
    // CM・広告関連
    { pattern: /CM|コマーシャル|広告|スポンサー|宣伝/, keyword: 'CM' },
    
    // 対談・インタビュー関連
    { pattern: /インタビュー|対談|質問|回答|お話|聞く|話す/, keyword: '対談' },
    
    // 重要・注意関連
    { pattern: /重要|大切|ポイント|注意|気をつけ|必要|大事/, keyword: '重要' },
    
    // 時間・タイミング関連
    { pattern: /時間|分|秒|早い|遅い|タイミング|今|今日|今回/, keyword: '時間' },
    
    // 場所・位置関連  
    { pattern: /場所|ここ|そこ|あそこ|近く|遠く|隣|前|後ろ/, keyword: '場所' },
    
    // 感情・評価関連
    { pattern: /良い|悪い|美味し|まずい|楽し|つまらない|面白い|素晴らし/, keyword: '評価' },
    
    // 人物関連
    { pattern: /先生|さん|氏|先輩|後輩|友達|家族|お客/, keyword: '人物' }
  ];
  
  // マッチしたキーワードを収集
  const foundKeywords = [];
  
  for (const { pattern, keyword } of keywordPatterns) {
    if (pattern.test(textStr)) {
      foundKeywords.push(keyword);
    }
  }
  
  // 重複削除して最大3個まで
  const uniqueKeywords = [...new Set(foundKeywords)].slice(0, 3);
  
  // キーワードが見つからない場合は文字数で判定
  if (uniqueKeywords.length === 0) {
    if (textStr.length < 20) {
      return '短文';
    } else if (textStr.length > 100) {
      return '長文';
    } else {
      return '一般';
    }
  }
  
  return uniqueKeywords.join(', ');
}

/**
 * CSV専用シート作成
 */
function createCSVSheet(csvData) {
  const spreadsheet = SpreadsheetApp.getActiveSpreadsheet();
  
  // 既存のCSVシート削除
  const existingSheet = spreadsheet.getSheetByName('DaVinci用CSV');
  if (existingSheet) {
    spreadsheet.deleteSheet(existingSheet);
  }
  
  // 新しいCSVシート作成
  const csvSheet = spreadsheet.insertSheet('DaVinci用CSV');
  
  // データ書き込み
  if (csvData.length > 0) {
    const range = csvSheet.getRange(1, 1, csvData.length, csvData[0].length);
    range.setValues(csvData);
    
    // ヘッダー書式設定
    const headerRange = csvSheet.getRange(1, 1, 1, csvData[0].length);
    headerRange.setFontWeight('bold');
    headerRange.setBackground('#E8F4F8');
    
    // カラム幅自動調整
    csvSheet.autoResizeColumns(1, csvData[0].length);
    
    // データ行に軽い背景色
    if (csvData.length > 1) {
      const dataRange = csvSheet.getRange(2, 1, csvData.length - 1, csvData[0].length);
      dataRange.setBackground('#FAFAFA');
    }
  }
  
  Logger.log('✅ "DaVinci用CSV"シートを作成しました');
}

/**
 * CSV文字列として出力
 */
function generateCSVString() {
  const sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName('DaVinci用CSV');
  
  if (!sheet) {
    Logger.log('❌ DaVinci用CSVシートが見つかりません。先にgenerateDaVinciCSV()を実行してください。');
    return null;
  }
  
  const data = sheet.getDataRange().getValues();
  
  // CSV文字列生成
  const csvString = data.map(row => 
    row.map(cell => `"${cell.toString()}"`).join(',')
  ).join('\n');
  
  Logger.log('=== CSV文字列生成完了 ===');
  Logger.log('以下をコピーしてファイル保存してください:');
  Logger.log('');
  Logger.log(csvString);
  
  return csvString;
}

/**
 * ワンクリック実行 - Step 3
 */
function executeStep3() {
  Logger.log('🚀 Step 3: DaVinci用CSV生成実行開始');
  
  try {
    // CSV生成
    const result = generateDaVinciCSV();
    
    Logger.log('');
    Logger.log('🎉 Step 3 完了！');
    Logger.log('"DaVinci用CSV"シートが作成されました');
    Logger.log('このCSVデータをDaVinciで使用できます');
    Logger.log('');
    Logger.log('📋 次のステップ:');
    Logger.log('1. "DaVinci用CSV"シートからデータをコピー');
    Logger.log('2. CSVファイルとして保存');
    Logger.log('3. DaVinciのコンソールで実行');
    
    return result;
    
  } catch (error) {
    Logger.log(`💥 実行エラー: ${error.message}`);
    return null;
  }
}