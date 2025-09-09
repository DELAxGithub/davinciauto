/**
 * @fileoverview Google Apps Script to process Premiere Pro transcript CSVs
 * for an XML generation pipeline.
 *
 * This script provides a 3-step workflow via a custom menu in Google Sheets:
 * 1. Format a raw Premiere transcript into a structure compatible with the Python script.
 * 2. Extract rows that have been manually colored for use in the final edit.
 * 3. Generate a final CSV for download, converting empty rows into timed gaps.
 */

// --- グローバル設定 ---

const FORMATTED_SHEET_SUFFIX = '_Formatted_for_XML';
const SELECTED_SHEET_SUFFIX = '_Selected_for_Cut';
const GAP_DURATION_SECONDS = 20;
const FPS = 30;

// Pythonスクリプトは各クリップの前後に149フレームのギャップを追加します。
// 目的のギャップ(20秒=600フレーム)を作るには、ダミークリップの長さを調整します。
// 600フレーム = 149 (前) + ダミークリップ長 + 149 (後)
// => ダミークリップ長 = 600 - 298 = 302 フレーム
const GAP_CLIP_DURATION_FRAMES = (GAP_DURATION_SECONDS * FPS) - (149 * 2);

// Pythonスクリプトが期待するCSVヘッダー
const TARGET_HEADERS = ['Speaker Name', 'イン点', 'アウト点', '文字起こし', '色選択'];

// Pythonスクリプトで定義されているPremiere Proのラベルカラー
const VALID_COLORS = [
  'Violet', 'Rose', 'Mango', 'Yellow', 'Lavender', 'Caribbean',
  'Tan', 'Forest', 'Blue', 'Purple', 'Teal', 'Brown', 'Gray',
  'Iris', 'Cerulean', 'Magenta'
];

// 色名から薄い背景色への対応表
const COLOR_MAP = {
  'Violet': '#E8D5F2',      // 薄い紫
  'Rose': '#F2D5E8',        // 薄いローズ
  'Mango': '#FFE6CC',       // 薄いマンゴー
  'Yellow': '#FFF2CC',      // 薄い黄色
  'Lavender': '#E6E6FA',    // 薄いラベンダー
  'Caribbean': '#CCF2F2',   // 薄いカリビアン
  'Tan': '#F2E6D9',         // 薄いタン
  'Forest': '#D9F2D9',      // 薄い森色
  'Blue': '#CCE6FF',        // 薄い青
  'Purple': '#E0CCFF',      // 薄い紫
  'Teal': '#CCFFE6',        // 薄いティール
  'Brown': '#E6D9CC',       // 薄い茶色
  'Gray': '#E6E6E6',        // 薄いグレー
  'Iris': '#D9CCFF',        // 薄いアイリス
  'Cerulean': '#CCF2FF',    // 薄いセルリアン
  'Magenta': '#FFCCF2'      // 薄いマゼンタ
};


/**
 * スプレッドシートを開いたときにカスタムメニューを追加します。
 */
function onOpen() {
  SpreadsheetApp.getUi()
    .createMenu('Premiere XML Helper')
    .addItem('Step 1: 生の文字起こしをフォーマット', 'step1_formatTranscript')
    .addItem('Step 2: 色付けした行を抽出', 'step2_extractColoredRows')
    .addItem('Step 3: 最終CSVを生成・ダウンロード', 'step3_generateAndDownloadCsv')
    .addSeparator()
    .addItem('Step 4: 色選択に基づいて文字起こし列を塗りつぶし', 'step4_colorTextCells')
    .addToUi();
}

/**
 * Step 1: Premiereの生CSVを読み込み、Pythonスクリプトに適した形式に変換して新しいシートに挿入します。
 */
function step1_formatTranscript() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const sourceSheet = ss.getActiveSheet();
  const sourceData = sourceSheet.getDataRange().getValues();

  if (sourceData.length < 2) {
    SpreadsheetApp.getUi().alert('ソースシートが空か、ヘッダーしかありません。');
    return;
  }

  const sourceHeaders = sourceData[0];
  const speakerCol = sourceHeaders.indexOf('Speaker Name');
  const startCol = sourceHeaders.indexOf('Start Time');
  const endCol = sourceHeaders.indexOf('End Time');
  const textCol = sourceHeaders.indexOf('Text');

  if ([speakerCol, startCol, endCol, textCol].includes(-1)) {
    SpreadsheetApp.getUi().alert('必要なヘッダー("Speaker Name", "Start Time", "End Time", "Text")が見つかりません。正しいシートを選択しているか確認してください。');
    return;
  }

  const formattedSheetName = sourceSheet.getName() + FORMATTED_SHEET_SUFFIX;
  let formattedSheet = ss.getSheetByName(formattedSheetName);
  if (formattedSheet) {
    formattedSheet.clear();
  } else {
    formattedSheet = ss.insertSheet(formattedSheetName);
  }
  ss.setActiveSheet(formattedSheet);

  const newData = [TARGET_HEADERS];
  for (let i = 1; i < sourceData.length; i++) {
    const row = sourceData[i];
    const newRow = [];
    newRow[TARGET_HEADERS.indexOf('Speaker Name')] = row[speakerCol];
    newRow[TARGET_HEADERS.indexOf('イン点')] = row[startCol].toString().replace(/;/g, ':');
    newRow[TARGET_HEADERS.indexOf('アウト点')] = row[endCol].toString().replace(/;/g, ':');
    newRow[TARGET_HEADERS.indexOf('文字起こし')] = row[textCol];
    newRow[TARGET_HEADERS.indexOf('色選択')] = '';   // 手動で入力
    newData.push(newRow);
  }

  formattedSheet.getRange(1, 1, newData.length, TARGET_HEADERS.length).setValues(newData);

  const colorColumnIndex = TARGET_HEADERS.indexOf('色選択') + 1;
  const rule = SpreadsheetApp.newDataValidation().requireValueInList(VALID_COLORS, true).build();
  formattedSheet.getRange(2, colorColumnIndex, formattedSheet.getMaxRows() - 1, 1).setDataValidation(rule);

  TARGET_HEADERS.forEach((_, i) => formattedSheet.autoResizeColumn(i + 1));

  SpreadsheetApp.getUi().alert(`Step 1 完了。 "${formattedSheetName}" シートを作成しました。\n\n次に、このシートで "色選択" の列を編集してください。`);
}

/**
 * Step 2: "Formatted"シートから色が割り当てられた行を抽出し、並べ替え用の新しい"Selected"シートにコピーします。
 */
function step2_extractColoredRows() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  
  // Formatted シートを探す（接尾辞で終わるシート名を検索）
  const sheets = ss.getSheets();
  const formattedSheets = sheets.filter(sheet => sheet.getName().endsWith(FORMATTED_SHEET_SUFFIX));

  if (formattedSheets.length === 0) {
    SpreadsheetApp.getUi().alert(`"${FORMATTED_SHEET_SUFFIX}" で終わるシートが見つかりません。Step 1を先に実行してください。`);
    return;
  }

  let formattedSheet;
  if (formattedSheets.length === 1) {
    formattedSheet = formattedSheets[0];
  } else {
    // 複数のFormattedシートがある場合、選択ダイアログを表示
    const ui = SpreadsheetApp.getUi();
    const sheetNames = formattedSheets.map(sheet => sheet.getName());
    ui.showModalDialog(
      HtmlService.createHtmlOutput(`
        <html>
          <body>
            <p>処理するFormattedシートを選択してください：</p>
            <select id="sheetSelect" style="width: 300px; padding: 5px;">
              ${sheetNames.map(name => `<option value="${name}">${name}</option>`).join('')}
            </select>
            <br><br>
            <button onclick="selectSheet()" style="padding: 8px 16px;">選択</button>
            <script>
              function selectSheet() {
                const select = document.getElementById('sheetSelect');
                google.script.run
                  .withSuccessHandler(google.script.host.close)
                  .withFailureHandler((error) => alert('エラー: ' + error))
                  .step2_processSelectedSheet(select.value);
              }
            </script>
          </body>
        </html>
      `).setWidth(400).setHeight(200),
      '処理するシートを選択'
    );
    return; // ダイアログ処理後にstep2_processSelectedSheetが呼ばれる
  }

  // 単一シートの場合は直接処理
  step2_processSelectedSheet(formattedSheet.getName());
}

/**
 * Step 2の実際の処理を行う関数（シート選択後に呼ばれる）
 */
function step2_processSelectedSheet(formattedSheetName) {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const formattedSheet = ss.getSheetByName(formattedSheetName);

  if (!formattedSheet) {
    SpreadsheetApp.getUi().alert(`シート "${formattedSheetName}" が見つかりません。`);
    return;
  }

  const data = formattedSheet.getDataRange().getValues();
  const headers = data[0];
  const colorColumnIndex = headers.indexOf('色選択');

  if (colorColumnIndex === -1) {
    SpreadsheetApp.getUi().alert(`"${formattedSheet.getName()}" シートに "色選択" 列が見つかりません。`);
    return;
  }

  const coloredRows = data.slice(1).filter(row => row[colorColumnIndex].toString().trim() !== '');
  
  if (coloredRows.length === 0) {
    SpreadsheetApp.getUi().alert(`"${formattedSheet.getName()}" シートに色が付けられた行が見つかりませんでした。`);
    return;
  }

  // 色選択された行を処理し、色の変わり目に空行（NA連番）を挿入
  const selectedData = [headers];
  let naCounter = 1;
  
  for (let i = 0; i < coloredRows.length; i++) {
    // 色選択された行を追加
    selectedData.push(coloredRows[i]);
    
    // 次の行があり、かつ色が変わる場合のみ空行（NA連番）を追加
    if (i < coloredRows.length - 1) {
      const currentColor = coloredRows[i][colorColumnIndex].toString().trim();
      const nextColor = coloredRows[i + 1][colorColumnIndex].toString().trim();
      
      if (currentColor !== nextColor) {
        const naRow = Array(headers.length).fill('');
        naRow[headers.indexOf('Speaker Name')] = `NA${naCounter}`;
        selectedData.push(naRow);
        naCounter++;
      }
    }
  }

  const baseSheetName = formattedSheet.getName().replace(FORMATTED_SHEET_SUFFIX, '');
  const selectedSheetName = baseSheetName + SELECTED_SHEET_SUFFIX;
  
  let selectedSheet = ss.getSheetByName(selectedSheetName);
  if (selectedSheet) {
    selectedSheet.clear();
  } else {
    selectedSheet = ss.insertSheet(selectedSheetName);
  }
  ss.setActiveSheet(selectedSheet);

  selectedSheet.getRange(1, 1, selectedData.length, headers.length).setValues(selectedData);
  headers.forEach((_, i) => selectedSheet.autoResizeColumn(i + 1));

  SpreadsheetApp.getUi().alert(`Step 2 完了。 "${selectedSheetName}" シートを作成しました。\n\n次に行の順番を入れ替えたり、隙間として空行を挿入したりしてください。`);
}

/**
 * フレーム数を HH:MM:SS:FF 形式のタイムコードに変換します。
 * @param {number} totalFrames - 総フレーム数
 * @param {number} fps - フレームレート
 * @return {string} タイムコード文字列
 */
function framesToTimecode(totalFrames, fps) {
  const totalSeconds = Math.floor(totalFrames / fps);
  const frames = totalFrames % fps;
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = totalSeconds % 60;
  const pad = (num) => num.toString().padStart(2, '0');
  return `${pad(hours)}:${pad(minutes)}:${pad(seconds)}:${pad(frames)}`;
}

/**
 * Step 3: "Selected"シートを読み込み、空行をギャップに変換して、最終的なCSVのダウンロードリンクを生成します。
 */
function step3_generateAndDownloadCsv() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  
  // Selected シートを探す（接尾辞で終わるシート名を検索）
  const sheets = ss.getSheets();
  const selectedSheets = sheets.filter(sheet => sheet.getName().endsWith(SELECTED_SHEET_SUFFIX));

  if (selectedSheets.length === 0) {
    SpreadsheetApp.getUi().alert(`"${SELECTED_SHEET_SUFFIX}" で終わるシートが見つかりません。Step 2を先に実行してください。`);
    return;
  }

  let selectedSheet;
  if (selectedSheets.length === 1) {
    selectedSheet = selectedSheets[0];
  } else {
    // 複数のSelectedシートがある場合、選択ダイアログを表示
    const ui = SpreadsheetApp.getUi();
    const sheetNames = selectedSheets.map(sheet => sheet.getName());
    ui.showModalDialog(
      HtmlService.createHtmlOutput(`
        <html>
          <body>
            <p>CSV生成するSelectedシートを選択してください：</p>
            <select id="sheetSelect" style="width: 300px; padding: 5px;">
              ${sheetNames.map(name => `<option value="${name}">${name}</option>`).join('')}
            </select>
            <br><br>
            <button onclick="selectSheet()" style="padding: 8px 16px;">選択</button>
            <script>
              function selectSheet() {
                const select = document.getElementById('sheetSelect');
                google.script.run
                  .withSuccessHandler(google.script.host.close)
                  .withFailureHandler((error) => alert('エラー: ' + error))
                  .step3_processSelectedSheet(select.value);
              }
            </script>
          </body>
        </html>
      `).setWidth(400).setHeight(200),
      'CSV生成するシートを選択'
    );
    return; // ダイアログ処理後にstep3_processSelectedSheetが呼ばれる
  }

  // 単一シートの場合は直接処理
  step3_processSelectedSheet(selectedSheet.getName());
}

/**
 * Step 3の実際の処理を行う関数（シート選択後に呼ばれる）
 */
function step3_processSelectedSheet(selectedSheetName) {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const selectedSheet = ss.getSheetByName(selectedSheetName);

  if (!selectedSheet) {
    SpreadsheetApp.getUi().alert(`シート "${selectedSheetName}" が見つかりません。`);
    return;
  }

  const data = selectedSheet.getDataRange().getValues();
  const finalCsvRows = [TARGET_HEADERS];
  let gapCounter = 0;
  const gapOutTimecode = framesToTimecode(GAP_CLIP_DURATION_FRAMES, FPS);

  for (let i = 1; i < data.length; i++) {
    const row = data[i];
    if (row.every(cell => cell.toString().trim() === '')) {
      gapCounter++;
      const gapRow = Array(TARGET_HEADERS.length).fill('');
      gapRow[TARGET_HEADERS.indexOf('イン点')] = '00:00:00:00';
      gapRow[TARGET_HEADERS.indexOf('アウト点')] = gapOutTimecode;
      gapRow[TARGET_HEADERS.indexOf('文字起こし')] = `--- ${GAP_DURATION_SECONDS}s GAP ---`;
      gapRow[TARGET_HEADERS.indexOf('色選択')] = `GAP_${gapCounter}`; // 各ギャップを別クリップとして扱う
      finalCsvRows.push(gapRow);
    } else {
      finalCsvRows.push(row);
    }
  }

  const csvContent = finalCsvRows.map(row => row.map(cell => {
    let cellStr = cell.toString();
    if (/[",\n]/.test(cellStr)) {
      cellStr = '"' + cellStr.replace(/"/g, '""') + '"';
    }
    return cellStr;
  }).join(',')).join('\n');

  const fileName = `${ss.getName()}_final_cut.csv`;
  const html = `<html><body><p>CSVの生成が完了しました。下のリンクをクリックしてダウンロードしてください。</p><a href="data:text/csv;charset=utf-8,${encodeURIComponent(csvContent)}" download="${fileName}">Download ${fileName}</a></body></html>`;
  SpreadsheetApp.getUi().showModalDialog(HtmlService.createHtmlOutput(html).setWidth(400).setHeight(150), 'CSVをダウンロード');
}

/**
 * Step 4: 色選択の値に基づいてD列（文字起こし）のセルを薄い色で塗りつぶします。
 */
function step4_colorTextCells() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  
  // Selected シートを探す（接尾辞で終わるシート名を検索）
  const sheets = ss.getSheets();
  const selectedSheets = sheets.filter(sheet => sheet.getName().endsWith(SELECTED_SHEET_SUFFIX));

  if (selectedSheets.length === 0) {
    SpreadsheetApp.getUi().alert(`"${SELECTED_SHEET_SUFFIX}" で終わるシートが見つかりません。Step 2を先に実行してください。`);
    return;
  }

  let selectedSheet;
  if (selectedSheets.length === 1) {
    selectedSheet = selectedSheets[0];
  } else {
    // 複数のSelectedシートがある場合、選択ダイアログを表示
    const ui = SpreadsheetApp.getUi();
    const sheetNames = selectedSheets.map(sheet => sheet.getName());
    ui.showModalDialog(
      HtmlService.createHtmlOutput(`
        <html>
          <body>
            <p>色塗りするSelectedシートを選択してください：</p>
            <select id="sheetSelect" style="width: 300px; padding: 5px;">
              ${sheetNames.map(name => `<option value="${name}">${name}</option>`).join('')}
            </select>
            <br><br>
            <button onclick="selectSheet()" style="padding: 8px 16px;">選択</button>
            <script>
              function selectSheet() {
                const select = document.getElementById('sheetSelect');
                google.script.run
                  .withSuccessHandler(google.script.host.close)
                  .withFailureHandler((error) => alert('エラー: ' + error))
                  .step4_processSelectedSheet(select.value);
              }
            </script>
          </body>
        </html>
      `).setWidth(400).setHeight(200),
      '色塗りするシートを選択'
    );
    return; // ダイアログ処理後にstep4_processSelectedSheetが呼ばれる
  }

  // 単一シートの場合は直接処理
  step4_processSelectedSheet(selectedSheet.getName());
}

/**
 * Step 4の実際の処理を行う関数（シート選択後に呼ばれる）
 */
function step4_processSelectedSheet(selectedSheetName) {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const selectedSheet = ss.getSheetByName(selectedSheetName);

  if (!selectedSheet) {
    SpreadsheetApp.getUi().alert(`シート "${selectedSheetName}" が見つかりません。`);
    return;
  }

  const data = selectedSheet.getDataRange().getValues();
  const headers = data[0];
  const textColumnIndex = headers.indexOf('文字起こし') + 1; // 1-based index
  const colorColumnIndex = headers.indexOf('色選択');

  if (colorColumnIndex === -1) {
    SpreadsheetApp.getUi().alert(`"色選択" 列が見つかりません。`);
    return;
  }

  if (textColumnIndex === 0) {
    SpreadsheetApp.getUi().alert(`"文字起こし" 列が見つかりません。`);
    return;
  }

  // データ行を処理（ヘッダー行をスキップ）
  for (let i = 1; i < data.length; i++) {
    const row = data[i];
    const colorValue = row[colorColumnIndex].toString().trim();
    
    if (colorValue && COLOR_MAP[colorValue]) {
      const range = selectedSheet.getRange(i + 1, textColumnIndex); // 1-based index
      range.setBackground(COLOR_MAP[colorValue]);
    }
  }

  SpreadsheetApp.getUi().alert(`Step 4 完了。 "${selectedSheetName}" シートの文字起こし列を色選択に基づいて塗りつぶしました。`);
}