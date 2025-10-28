/*
 * Premiere Pro バッチAAF書き出しスクリプト
 * * 使い方:
 * 1. 下の「ユーザーが設定する項目」を2箇所、ご自身の環境に合わせて変更します。
 * 2. このファイルを「Batch_Export_AAF.jsx」などの名前で保存します。
 * 3. Premiere Proでプロジェクトを開いた状態で、[ファイル] > [スクリプト] > [スクリプトを実行...] を選択し、
 * 保存した .jsx ファイルを選びます。
 */

(function batchExportAAF() {

    // --- ▼ ユーザーが設定する項目 ▼ ---

    // 1. Premiere Pro プロジェクトパネル内のビン名
    //    AAFを書き出したいシーケンスが「すべて」入っているビンの名前を指定してください。
    //    （例: "03_MA_Export", "音声書き出し対象" など）
    var targetBinName = "AAFexport"; 

    // 2. AAFの保存先フォルダ
    //    書き出したAAFファイルを保存するPC上のフォルダパスを指定します。
    //    (注意: スラッシュは \ ではなく / を使ってください)
    //
    //    Windowsの例: "C:/Users/Dela/Desktop/AAF_Exports"
    //    macOSの例:   "~/Desktop/AAF_Exports"
    var outputFolderPath = "/Users/hiroshikodera/Library/CloudStorage/GoogleDrive-h.kodera@gmail.com/My Drive/Liberary_young6_MA";

    // --- ▲ ユーザーが設定する項目 ▲ ---


    // --- メイン処理 (ここから下は変更不要です) ---
    
    if (!app.project) {
        alert("プロジェクトが開かれていません。");
        return;
    }

    // 保存先フォルダのオブジェクトを作成
    var outputFolder = new Folder(outputFolderPath);
    if (!outputFolder.exists) {
        if (outputFolder.create()) {
            alert("保存先フォルダを新規作成しました:\n" + outputFolderPath);
        } else {
            alert("エラー: 保存先フォルダを作成できませんでした。\nパスが正しいか確認してください:\n" + outputFolderPath);
            return;
        }
    }

    // 指定されたビンをプロジェクト内から探す
    var targetBin = findBinByName(app.project.rootItem, targetBinName);

    if (!targetBin) {
        alert("エラー: ビンが見つかりません。\nビン名が正しいか確認してください: 「" + targetBinName + "」");
        return;
    }

    // ビンの中のシーケンスをリストアップ
    var sequencesToExport = [];
    for (var i = 0; i < targetBin.children.numItems; i++) {
        var item = targetBin.children[i];
        // item.type === 2 でも判定できますが、isSequence() の方が確実です
        if (item.isSequence) { 
             sequencesToExport.push(item);
        }
    }

    if (sequencesToExport.length === 0) {
        alert("ビン 「" + targetBinName + "」 の中にシーケンスが見つかりませんでした。");
        return;
    }

    alert(sequencesToExport.length + " 件のシーケンスをAAFとして書き出します。\n処理には時間がかかる場合があります。");

    var errorCount = 0;
    var errorLog = "以下のシーケンスの書き出しに失敗しました:\n";

    // リストアップしたシーケンスを順番に書き出し
    for (var j = 0; j < sequencesToExport.length; j++) {
        var currentSequence = sequencesToExport[j];
        
        // 保存するファイルパスを決定 (シーケンス名.aaf)
        var outputFilePath = outputFolder.fsName + "/" + currentSequence.name + ".aaf";
        var file = new File(outputFilePath);

        try {
            /*
             * exportAAF パラメータ詳細:
             * 1. filePath (string): 保存ファイルパス
             * 2. mixDownVideo (bool): ビデオをミックスダウンするか (音声用なので false)
             * 3. explodeTracks (bool): オーディオをモノラル分解するか (ポスプロ標準は true)
             * 4. sampleRate (int): サンプルレート (48000 Hz)
             * 5. bitsPerSample (int): ビット深度 (24 bit)
             * 6. embedAudio (bool): オーディオをAAFに埋め込むか (true が一般的)
             * 7. audioFileFormat (int): 0=AIFF, 1=Broadcast WAVE (1 の BWF を推奨)
             * 8. trimSources (bool): 使用部分のみ書き出すか (true)
             * 9. handleFrames (int): ハンドル（のりしろ）のフレーム数 (ここでは150フレームに設定)
             */
            app.project.exportAAF(
                currentSequence, // 対象シーケンス
                file.fsName,     // 1. ファイルパス
                false,           // 2. mixDownVideo
                true,            // 3. explodeTracks
                48000,           // 4. sampleRate
                24,              // 5. bitsPerSample
                true,            // 6. embedAudio
                1,               // 7. audioFileFormat (BWF)
                true,            // 8. trimSources
                150              // 9. handleFrames (約5秒 @30fps)
            );

        } catch (e) {
            errorCount++;
            errorLog += currentSequence.name + " (" + e.toString() + ")\n";
        }
    }

    // --- 完了報告 ---
    if (errorCount === 0) {
        alert("完了！\n" + sequencesToExport.length + " 件すべてのシーケンスをAAFとして書き出しました。\n保存先: " + outputFolderPath);
    } else {
        alert("処理が完了しましたが、" + errorCount + " 件のエラーが発生しました。\n\n" + errorLog + "\n保存先: " + outputFolderPath);
    }


    // --- ヘルパー関数: 再帰的にビンを探す ---
    function findBinByName(root, name) {
        for (var i = 0; i < root.children.numItems; i++) {
            var item = root.children[i];
            if (item.type === ProjectItemType.BIN) {
                if (item.name === name) {
                    return item; // 見つかった
                } else {
                    var found = findBinByName(item, name); // サブビンを再帰的に探す
                    if (found) return found;
                }
            }
        }
        return null; // 見つからなかった
    }

})();
