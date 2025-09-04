/**
 * Google Apps Script: CSV → EDL変換
 * cutlistからDaVinci Resolve用EDLファイルを生成
 */

function generateEDL() {
  // スプレッドシートから データ取得
  const sheet = SpreadsheetApp.getActiveSheet();
  const data = sheet.getDataRange().getValues();
  const headers = data[0];
  
  // カラムインデックス取得
  const startTimeCol = headers.indexOf('Start Time');
  const endTimeCol = headers.indexOf('End Time');
  const labelCol = headers.indexOf('Label');
  const colorGroupCol = headers.indexOf('Color Group');
  
  if (startTimeCol === -1 || endTimeCol === -1) {
    throw new Error('Start Time or End Time column not found');
  }
  
  // EDLヘッダー
  let edl = 'TITLE: Auto Generated Edit Points\\n';
  edl += 'FCM: NON-DROP FRAME\\n\\n';
  
  // データ行を処理
  let clipNumber = 1;
  
  for (let i = 1; i < data.length; i++) {
    const row = data[i];
    const startTime = row[startTimeCol];
    const endTime = row[endTimeCol];
    const label = row[labelCol] || `Clip${clipNumber}`;
    
    if (!startTime) continue;
    
    // タイムコード形式チェック・変換
    const formattedStartTime = formatTimecode(startTime);
    const formattedEndTime = endTime ? formatTimecode(endTime) : addOneFrame(formattedStartTime);
    
    if (!formattedStartTime) {
      console.log(`Skip invalid timecode at row ${i + 1}: ${startTime}`);
      continue;
    }
    
    // EDLエントリ生成
    // Format: 001  V     C        01:00:15:23 01:00:15:24 00:00:00:00 00:00:00:01
    const clipNumberStr = String(clipNumber).padStart(3, '0');
    const recordIn = '00:00:00:00';
    const recordOut = incrementTimecode(recordIn, clipNumber - 1);
    
    edl += `${clipNumberStr}  V     C        ${formattedStartTime} ${formattedEndTime} ${recordIn} ${recordOut}\\n`;
    edl += `* FROM CLIP NAME: ${label}\\n\\n`;
    
    clipNumber++;
  }
  
  // ファイル保存
  const fileName = `edit_points_${Utilities.formatDate(new Date(), 'GMT+9', 'yyyyMMdd_HHmmss')}.edl`;
  const blob = Utilities.newBlob(edl, 'text/plain', fileName);
  
  // Google Drive に保存
  const file = DriveApp.createFile(blob);
  
  console.log(`EDL generated: ${fileName}`);
  console.log(`File ID: ${file.getId()}`);
  console.log(`Total edit points: ${clipNumber - 1}`);
  
  return {
    fileName: fileName,
    fileId: file.getId(),
    downloadUrl: file.getDownloadUrl(),
    editPointCount: clipNumber - 1
  };
}

/**
 * タイムコードフォーマット統一
 */
function formatTimecode(input) {
  if (!input) return null;
  
  const str = input.toString().trim();
  
  // HH:MM:SS:FF 形式チェック
  const match = str.match(/^(\\d{2}):(\\d{2}):(\\d{2}):(\\d{2})$/);
  if (match) {
    return str; // 既に正しい形式
  }
  
  // 他の形式からの変換を試行
  const timeMatch = str.match(/^(\\d{1,2}):(\\d{2}):(\\d{2}):(\\d{2})$/);
  if (timeMatch) {
    const [, h, m, s, f] = timeMatch;
    return `${h.padStart(2, '0')}:${m}:${s}:${f}`;
  }
  
  console.log(`Invalid timecode format: ${str}`);
  return null;
}

/**
 * 1フレーム追加
 */
function addOneFrame(timecode, fps = 25) {
  const [h, m, s, f] = timecode.split(':').map(Number);
  
  let newFrames = f + 1;
  let newSeconds = s;
  let newMinutes = m;
  let newHours = h;
  
  if (newFrames >= fps) {
    newFrames = 0;
    newSeconds++;
    
    if (newSeconds >= 60) {
      newSeconds = 0;
      newMinutes++;
      
      if (newMinutes >= 60) {
        newMinutes = 0;
        newHours++;
      }
    }
  }
  
  return `${String(newHours).padStart(2, '0')}:${String(newMinutes).padStart(2, '0')}:${String(newSeconds).padStart(2, '0')}:${String(newFrames).padStart(2, '0')}`;
}

/**
 * タイムコード増分
 */
function incrementTimecode(baseTimecode, increment, fps = 25) {
  const [h, m, s, f] = baseTimecode.split(':').map(Number);
  
  let totalFrames = h * 3600 * fps + m * 60 * fps + s * fps + f;
  totalFrames += increment;
  
  const newFrames = totalFrames % fps;
  const totalSeconds = Math.floor(totalFrames / fps);
  const newSeconds = totalSeconds % 60;
  const totalMinutes = Math.floor(totalSeconds / 60);
  const newMinutes = totalMinutes % 60;
  const newHours = Math.floor(totalMinutes / 60);
  
  return `${String(newHours).padStart(2, '0')}:${String(newMinutes).padStart(2, '0')}:${String(newSeconds).padStart(2, '0')}:${String(newFrames).padStart(2, '0')}`;
}

/**
 * シンプル版: マーカーXML生成
 */
function generateMarkerXML() {
  const sheet = SpreadsheetApp.getActiveSheet();
  const data = sheet.getDataRange().getValues();
  const headers = data[0];
  
  const startTimeCol = headers.indexOf('Start Time');
  const labelCol = headers.indexOf('Label');
  const colorGroupCol = headers.indexOf('Color Group');
  
  let xml = '<?xml version="1.0" encoding="UTF-8"?>\\n';
  xml += '<markers>\\n';
  
  for (let i = 1; i < data.length; i++) {
    const row = data[i];
    const startTime = row[startTimeCol];
    const label = row[labelCol] || `Marker${i}`;
    const colorGroup = row[colorGroupCol] || 1;
    
    if (!startTime) continue;
    
    const formattedTime = formatTimecode(startTime);
    if (!formattedTime) continue;
    
    xml += `  <marker>\\n`;
    xml += `    <timecode>${formattedTime}</timecode>\\n`;
    xml += `    <name>${escapeXml(label)}</name>\\n`;
    xml += `    <color>${colorGroup}</color>\\n`;
    xml += `  </marker>\\n`;
  }
  
  xml += '</markers>\\n';
  
  const fileName = `markers_${Utilities.formatDate(new Date(), 'GMT+9', 'yyyyMMdd_HHmmss')}.xml`;
  const blob = Utilities.newBlob(xml, 'text/xml', fileName);
  const file = DriveApp.createFile(blob);
  
  return {
    fileName: fileName,
    fileId: file.getId(),
    downloadUrl: file.getDownloadUrl()
  };
}

/**
 * XML特殊文字エスケープ
 */
function escapeXml(str) {
  if (!str) return '';
  return str.toString()
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

/**
 * テスト実行
 */
function testGeneration() {
  console.log('Testing EDL generation...');
  const edlResult = generateEDL();
  console.log('EDL Result:', edlResult);
  
  console.log('Testing XML generation...');
  const xmlResult = generateMarkerXML();
  console.log('XML Result:', xmlResult);
}