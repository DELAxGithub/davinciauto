function createXMLString() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const sheet = ss.getActiveSheet();
  const sheetName = sheet.getName();
  const lastRow = sheet.getLastRow();
  const texts = sheet.getRange(1, 1, lastRow).getValues();

  let xmlContent = '<?xml version="1.0" encoding="utf-8"?><xmeml version="5"><sequence id="video"><name>' + sheetName + '</name><duration>6639.900000000001</duration><rate><timebase>30</timebase><ntsc>false</ntsc></rate><media><video><format><samplecharacteristics><width>1920</width><height>1080</height><anamorphic>false</anamorphic><pixelaspectratio>square</pixelaspectratio><fielddominance>none</fielddominance></samplecharacteristics></format><track>';

let validRowCount = 0; // 有効な行数をカウント

for (let i = 0; i < lastRow; i++) {
    const text = texts[i][0];
    // 空欄をスキップ
    if (!text || text.trim() === '') {
        continue;
    }

    const cleanText = text.replace(/\n/g, '&#13;'); // 改行をXMLで使えるコードに置き換え
    const start = validRowCount * (240 + 150); // 有効な行数に基づいて開始位置を計算
    const end = start + 240;
    
    validRowCount++; // 有効な行をカウントアップ

    const fixedXmlPart = '<generatoritem id="Outline Text1"><name>Outline Text</name><duration>6639.900000000001</duration><rate><timebase>30</timebase><ntsc>false</ntsc></rate><start>#VALUE!</start><end>#VALUE!</end><enabled>true</enabled><anamorphic>false</anamorphic><alphatype>black</alphatype><masterclipid>Outline Text1</masterclipid><effect><name>Outline Text</name><effectid>Outline Text</effectid><effectcategory>Text</effectcategory><effecttype>generator</effecttype><pproExpanded>false</pproExpanded><mediatype>video</mediatype><parameter><parameterid>part1</parameterid><name>Text Settings</name><value/></parameter><parameter><parameterid>str</parameterid><name>Text</name><value>石油が発見される 以前は&#13;</value></parameter><parameter><parameterid>font</parameterid><name>Font</name><value>HiraginoSans-W6</value></parameter><parameter><parameterid>style</parameterid><name>Style</name><valuemin>1</valuemin><valuemax>1</valuemax><valuelist><valueentry><name>Regular</name><value>1</value></valueentry></valuelist><value>1</value></parameter><parameter><parameterid>align</parameterid><name>Alignment</name><valuemin>1</valuemin><valuemax>3</valuemax><valuelist><valueentry><name>Left</name><value>1</value></valueentry><valueentry><name>Center</name><value>2</value></valueentry><valueentry><name>Right</name><value>3</value></valueentry></valuelist><value>2</value></parameter><parameter><parameterid>size</parameterid><name>Size</name><valuemin>0</valuemin><valuemax>200</valuemax><value>24</value></parameter><parameter><parameterid>track</parameterid><name>Tracking</name><valuemin>0</valuemin><valuemin>100</valuemax><value>1</value></parameter><parameter><parameterid>lead</parameterid><name>Leading</name><valuemin>-100</valuemin><valuemax>100</valuemax><value>0</value></parameter><parameter><parameterid>aspect</parameterid><name>Aspect</name><valuemin>0</valuemin><valuemax>4</valuemax><value>1</value></parameter><parameter><parameterid>linewidth</parameterid><name>Line Width</name><valuemin>0</valuemin><valuemax>200</valuemax><value>0</value></parameter><parameter><parameterid>linesoft</parameterid><name>Line Softness</name><valuemin>0</valuemin><valuemax>100</valuemax><value>5</value></parameter><parameter><parameterid>textopacity</parameterid><name>Text Opacity</name><valuemin>0</valuemin><valuemax>100</valuemax><value>100</value></parameter><parameter><parameterid>center</parameterid><name>Center</name><value><horiz>0</horiz><vert>0.43</vert></value></parameter><parameter><parameterid>textcolor</parameterid><name>Text Color</name><value><alpha>255</alpha><red>255</red><green>255</green><blue>255</blue></value></parameter><parameter><parameterid>supertext</parameterid><name>Text Graphic</name></parameter><parameter><parameterid>linecolor</parameterid><name>Line Color</name><value><alpha>255</alpha><red>255</red><green>255</green><blue>255</blue></value></parameter><parameter><parameterid>superline</parameterid><name>Line Graphic</name></parameter><parameter><parameterid>part2</parameterid><name>Background Settings</name><value/></parameter><parameter><parameterid>xscale</parameterid><name>Horizontal Size</name><valuemin>0</valuemin><valuemax>200</valuemax><value>0</value></parameter><parameter><parameterid>yscale</parameterid><name>Vertical Size</name><valuemin>0</valuemin><valuemax>200</valuemax><value>0</value></parameter><parameter><parameterid>xoffset</parameterid><name>Horizontal Offset</name><valuemin>-100</valuemin><valuemax>100</valuemax><value>0</value></parameter><parameter><parameterid>yoffset</parameterid><name>Vertical Offset</name><valuemin>-100</valuemin><valuemax>100</valuemax><value>0</value></parameter><parameter><parameterid>backsoft</parameterid><name>Back Soft</name><valuemin>0</valuemin><valuemax>100</valuemax><value>0</value></parameter><parameter><parameterid>backopacity</parameterid><name>Back Opacity</name><valuemin>0</valuemin><valuemax>100</valuemax><value>50</value></parameter><parameter><parameterid>backcolor</parameterid><name>Back Color</name><value><alpha>255</alpha><red>255</red><green>255</green><blue>255</blue></value></parameter><parameter><parameterid>superback</parameterid><name>Back Graphic</name></parameter><parameter><parameterid>crop</parameterid><name>Crop</name><value>false</value></parameter><parameter><parameterid>motionblur</parameterid><name>Motion Blur</name><value>false</value></parameter><parameter><parameterid>filter</parameterid><name>Filter</name><valuemin>1</valuemin><valuemax>1</valuemax><valuelist><valueentry><name>None</name><value>1</value></valueentry></valuelist><value>1</value></parameter><parameter><parameterid>motionbluramnt</parameterid><name>Motion Blur Amount</name><valuemin>0</valuemin><valuemax>100</valuemax><value>0</value></parameter></effect></generatoritem>';

    const newTextPart = fixedXmlPart.replace('#VALUE!', start).replace('#VALUE!', end).replace('石油が発見される 以前は&#13;', text);
    xmlContent += newTextPart;
  }

  xmlContent += '</track></video></media></sequence></xmeml>';

  const folder = DriveApp.getFoldersByName('XMLフォルダ').next();

  // 既存のファイルを削除する
  const files = folder.getFilesByName(sheetName + '.xml');
  while (files.hasNext()) {
    files.next().setTrashed(true);
  }

  // 新しいXMLファイルを作成する
  const xmlFile = folder.createFile(sheetName + '.xml', xmlContent, MimeType.PLAIN_TEXT);
}

function onOpen() {
  var ui = SpreadsheetApp.getUi();
  ui.createMenu('カスタムメニュー')
    .addItem('XML作成', 'createXMLString')
    .addItem('シート削除', 'deleteSheetsExcept')
    .addItem('シート非表示', 'hideSheets')
    .addItem('タイムコード','processTimecodes')
    .addToUi();
}

function showDownloadDialog() {
  const html = HtmlService.createHtmlOutputFromFile('DownloadDialog')
      .setWidth(300)
      .setHeight(100);
  SpreadsheetApp.getUi().showModalDialog(html, 'XMLファイルをダウンロード');
}


function processTimecodes() {
  // スプレッドシートとシートを取得
  const sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName("audio_info");
  if (!sheet) {
    throw new Error("シート 'audio_info' が見つかりません");
  }

  // データの範囲を取得
  const data = sheet.getDataRange().getValues();
  const output = [];

  // データの処理（1行目はヘッダーなのでスキップ）
  for (let i = 1; i < data.length; i++) {
    const row = data[i];
    const inPoint = row[1]; // B列（イン点）
    const duration = row[3]; // D列（デュレーション）

    // B列のタイムコードをMMSS形式に変換
    const inCode = formatToMMSSWithReset(inPoint);

    // D列のデュレーションを秒数に変換し、繰り上げ処理（000を省略）
    const durationMMSS = formatDuration(duration);

    // フォーマットされた文字列を作成
    const resultText = `${inCode}（${durationMMSS}）`;
    output.push([resultText]);
  }

  // 結果を新しい列に出力
  sheet.getRange(2, 9, output.length, 1).setValues(output); // I列に出力
}

// タイムコードをMMSS形式に変換し、1時間を超えた場合リセットする関数
function formatToMMSSWithReset(timecode) {
  const parts = timecode.split(":");
  if (parts.length < 3) return "0000"; // 不正なデータは0000にする

  const hours = parseInt(parts[0], 10);
  const minutes = parseInt(parts[1], 10);
  const secondsAndFrames = parts[2].split(".");
  const seconds = parseInt(secondsAndFrames[0], 10);

  // 総時間を秒に計算
  let totalSeconds = hours * 3600 + minutes * 60 + seconds;

  // 60分単位でリセット
  const mm = Math.floor(totalSeconds / 60) % 60; // 分（60分でリセット）
  const ss = totalSeconds % 60; // 秒

  return ("00" + mm).slice(-2) + ("00" + ss).slice(-2); // MMSS形式を返す
}

// デュレーションを秒数に変換し、「000」を省略する関数
function formatDuration(duration) {
  const parts = duration.split(":");
  if (parts.length < 3) return "0"; // 不正なデータは0秒にする

  const hours = parseInt(parts[0], 10);
  const minutes = parseInt(parts[1], 10);
  const secondsAndFrames = parts[2].split(".");
  const seconds = parseInt(secondsAndFrames[0], 10);
  const frames = secondsAndFrames[1] ? parseInt(secondsAndFrames[1], 10) : 0;

  // 総時間を秒に計算し、フレームが20以上なら1秒繰り上げ
  let totalSeconds = hours * 3600 + minutes * 60 + seconds;
  if (frames >= 20) {
    totalSeconds++;
  }

  // 000を省略（単純に秒数だけ返す）
  return totalSeconds.toString();
}