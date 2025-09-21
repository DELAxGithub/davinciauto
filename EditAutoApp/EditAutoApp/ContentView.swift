import SwiftUI
import AppKit
import UniformTypeIdentifiers

private enum Provider: String, CaseIterable, Identifiable {
    case elevenlabs
    var id: String { rawValue }
    var displayName: String {
        switch self {
        case .elevenlabs: return "ElevenLabs"
        }
    }
    var keychainAccount: String { rawValue }
}

struct ContentView: View {
    @State private var selfCheckResult: SelfCheckResult?
    @State private var selfCheckStatus: String = "未実行"
    @State private var selfCheckPassed = false

    @State private var scriptURL: URL?
    @State private var outputBookmark: Data?

    @State private var selectedProvider: Provider = .elevenlabs
    @State private var apiKey: String = ""
    @State private var savedAPIKey: String = ""

    @State private var concurrency: Int = 1

    @State private var events: [String] = []
    @State private var statusMessage: String = ""
    @State private var isRunning = false
    @State private var lastEventDate = Date()
    @State private var heartbeatTimer: Timer?

    private let checker = SelfCheckService()
    private let pipeline = PipelineCLIService()

    var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            GroupBox("環境チェック") {
                VStack(alignment: .leading, spacing: 8) {
                    HStack {
                        Button("Self-Check 実行", action: runSelfCheck)
                            .disabled(isRunning)
                        Text(selfCheckStatus)
                            .foregroundStyle(selfCheckPassed ? .green : .secondary)
                    }
                    if let info = selfCheckResult {
                        VStack(alignment: .leading, spacing: 4) {
                            if let deps = info.deps {
                                Text("pydub: \(deps["pydub"] ?? "?")")
                            }
                            if let ff = info.ffmpeg, !ff.isEmpty { Text("ffmpeg: \(ff)") }
                            if let fp = info.ffprobe, !fp.isEmpty { Text("ffprobe: \(fp)") }
                            if let err = info.error, !info.ok {
                                Text("エラー: \(err)").foregroundStyle(.red)
                            }
                        }
                        .font(.caption)
                        .foregroundStyle(.secondary)
                    }
                }
            }

            GroupBox("入力・設定") {
                VStack(alignment: .leading, spacing: 12) {
                    HStack {
                        Button("台本ファイルを選ぶ…", action: chooseScript)
                            .disabled(isRunning)
                        Text(scriptURL?.lastPathComponent ?? "未選択")
                            .foregroundStyle(.secondary)
                    }
                    HStack {
                        Button("出力フォルダを選ぶ…", action: chooseOutput)
                            .disabled(isRunning)
                        Text(outputBookmark == nil ? "未選択" : "選択済み")
                            .foregroundStyle(.secondary)
                    }
                    Picker("TTSプロバイダ", selection: $selectedProvider) {
                        ForEach(Provider.allCases) { provider in
                            Text(provider.displayName).tag(provider)
                        }
                    }
                    .pickerStyle(.segmented)

                    VStack(alignment: .leading, spacing: 6) {
                        SecureField("APIキー (Keychainに保存)", text: $apiKey)
                            .textFieldStyle(.roundedBorder)
                            .disabled(isRunning)
                        HStack {
                            Button("保存", action: saveAPIKey).disabled(apiKey.isEmpty)
                            Button("削除", role: .destructive, action: deleteAPIKey)
                                .disabled(savedAPIKey.isEmpty)
                            Text(savedAPIKey.isEmpty ? "未保存" : "保存済み")
                                .foregroundStyle(.secondary)
                        }
                    }

                    Stepper(value: $concurrency, in: 1...4) {
                        Text("並列度 \(concurrency)")
                    }
                    .disabled(isRunning)
                }
            }

            HStack(spacing: 12) {
                Button(isRunning ? "実行中…" : "Fake-TTS で実行", action: runPipeline)
                    .disabled(isRunning || !selfCheckPassed || scriptURL == nil || outputBookmark == nil)
                Button("停止", role: .destructive, action: stopPipeline)
                    .disabled(!isRunning)
            }

            if !statusMessage.isEmpty {
                Text(statusMessage)
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
            }

            Divider()
            Text("進捗イベント (最新が下)")
                .font(.headline)
            ScrollView {
                LazyVStack(alignment: .leading, spacing: 6) {
                    ForEach(events.indices, id: \.self) { idx in
                        Text(events[idx])
                            .font(.system(.body, design: .monospaced))
                            .frame(maxWidth: .infinity, alignment: .leading)
                    }
                }
            }
        }
        .padding(20)
        .frame(minWidth: 640, minHeight: 540)
        .onAppear(perform: loadSavedKey)
        .onChange(of: selectedProvider) { _ in loadSavedKey() }
    }

    private func runSelfCheck() {
        selfCheckStatus = "チェック中…"
        selfCheckPassed = false
        checker.run { result in
            DispatchQueue.main.async {
                switch result {
                case .success(let info):
                    self.selfCheckResult = info
                    if info.ok {
                        selfCheckStatus = "OK"
                        selfCheckPassed = true
                    } else {
                        selfCheckStatus = "NG: \(info.error ?? "不明")"
                        selfCheckPassed = false
                    }
                case .failure(let code):
                    selfCheckResult = nil
                    selfCheckStatus = "NG (exit \(code.rawValue))"
                    selfCheckPassed = false
                }
            }
        }
    }

    private func runPipeline() {
        guard let scriptURL, let outputBookmark else { return }
        events.removeAll()
        statusMessage = "実行中…"
        isRunning = true
        lastEventDate = Date()
        startHeartbeatMonitor()

        let apiKeyValue = KeychainService.load(service: "com.editauto.tts", account: selectedProvider.keychainAccount) ?? ""
        let request = RunRequest(
            projectId: UUID().uuidString,
            scriptURL: scriptURL,
            outputBookmark: outputBookmark,
            target: "resolve",
            provider: selectedProvider.rawValue,
            frameRate: 23.976,
            fakeTTS: true,
            concurrency: concurrency,
            apiKey: apiKeyValue
        )

        pipeline.run(request, onEvent: handleEvent(_:), onExit: handleExit(_:))
    }

    private func stopPipeline() {
        pipeline.cancel()
        statusMessage = "停止要求を送信しました…"
    }

    private func chooseScript() {
        let panel = NSOpenPanel()
        panel.allowsMultipleSelection = false
        panel.canChooseDirectories = false
        panel.canChooseFiles = true
        panel.allowedContentTypes = [.plainText]
        if panel.runModal() == .OK {
            scriptURL = panel.url
        }
    }

    private func chooseOutput() {
        let panel = NSOpenPanel()
        panel.canCreateDirectories = true
        panel.canChooseDirectories = true
        panel.canChooseFiles = false
        panel.allowsMultipleSelection = false
        if panel.runModal() == .OK, let url = panel.url {
            if let bookmark = try? url.bookmarkData(options: .withSecurityScope, includingResourceValuesForKeys: nil, relativeTo: nil) {
                outputBookmark = bookmark
            }
        }
    }

    private func saveAPIKey() {
        do {
            try KeychainService.save(service: "com.editauto.tts", account: selectedProvider.keychainAccount, secret: apiKey)
            savedAPIKey = apiKey
            apiKey = ""
            statusMessage = "APIキーを保存しました。"
        } catch {
            statusMessage = "Keychain保存に失敗しました"
        }
    }

    private func deleteAPIKey() {
        KeychainService.delete(service: "com.editauto.tts", account: selectedProvider.keychainAccount)
        savedAPIKey = ""
        statusMessage = "APIキーを削除しました。"
    }

    private func loadSavedKey() {
        savedAPIKey = KeychainService.load(service: "com.editauto.tts", account: selectedProvider.keychainAccount) ?? ""
    }

    private func handleEvent(_ event: [String: Any]) {
        DispatchQueue.main.async {
            lastEventDate = Date()
            events.append(render(event))

            guard let type = event["type"] as? String else { return }
            switch type {
            case "rate_limit":
                statusMessage = "レート制限中。自動で並列度1で再実行してください。"
                concurrency = 1
            case "heartbeat":
                break
            case "aborted":
                statusMessage = "処理を中断しました。"
            case "done":
                statusMessage = "完了しました。"
            default:
                break
            }
        }
    }

    private func handleExit(_ code: ExitCode) {
        DispatchQueue.main.async {
            stopHeartbeatMonitor()
            isRunning = false
            statusMessage = guidance(for: code)
        }
    }

    private func render(_ event: [String: Any]) -> String {
        guard let type = event["type"] else { return "<unknown>" }
        var parts: [String] = ["type=\(type)"]
        if let seq = event["seq"] { parts.append("seq=\(seq)") }
        if let ts = event["ts"] { parts.append("ts=\(ts)") }
        switch type as? String {
        case "segment_generated":
            if let idx = event["index"], let total = event["total"] {
                parts.append("segment=\(idx)/\(total)")
            }
        case "rate_limit":
            if let retry = event["retry_after"] { parts.append("retry_after=\(retry)") }
        case "aborted":
            parts.append("reason=abort")
        default:
            break
        }
        return parts.joined(separator: " ")
    }

    private func startHeartbeatMonitor() {
        heartbeatTimer?.invalidate()
        heartbeatTimer = Timer.scheduledTimer(withTimeInterval: 5.0, repeats: true) { _ in
            let delta = Date().timeIntervalSince(self.lastEventDate)
            if delta > 8.0 {
                DispatchQueue.main.async {
                    self.statusMessage = "5秒以上更新がありません。ハングしていないか確認してください。"
                }
            }
        }
    }

    private func stopHeartbeatMonitor() {
        heartbeatTimer?.invalidate()
        heartbeatTimer = nil
    }

    private func guidance(for code: ExitCode) -> String {
        switch code {
        case .ok:
            return "成功しました。"
        case .usage:
            return "入力が不足/不正です。台本・出力先・設定を確認してください。"
        case .unavailable:
            return "環境要件 (pydub/ffmpeg/ffprobe) が不足しています。Self-Checkを確認してください。"
        case .cantCreate:
            return "書き込みに失敗しました。出力フォルダを再承認してください。"
        case .tempFail:
            return "一時的な失敗 / 中断 / レート制限です。再試行してください。"
        }
    }
}

#Preview {
    ContentView()
}
