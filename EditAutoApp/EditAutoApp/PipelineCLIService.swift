import Foundation

struct RunRequest {
    let projectId: String
    let scriptURL: URL
    let outputBookmark: Data
    let target: String
    let provider: String
    let frameRate: Double
    let fakeTTS: Bool
    let concurrency: Int
    let apiKey: String
}

final class PipelineCLIService {
    private var process: Process?
    private var tailer: JSONLTailer?

    func run(_ request: RunRequest,
             onEvent: @escaping ([String: Any]) -> Void,
             onExit: @escaping (ExitCode) -> Void) {
        DispatchQueue.global(qos: .userInitiated).async {
            do {
                let env = try PythonRuntime.environment()
                let python = try PythonRuntime.resolve().executable
                let logURL = FileManager.default.temporaryDirectory.appendingPathComponent("progress-\(UUID().uuidString).jsonl")
                FileManager.default.createFile(atPath: logURL.path, contents: nil)

                var stale = false
                let outputURL = try URL(resolvingBookmarkData: request.outputBookmark, options: .withSecurityScope, relativeTo: nil, bookmarkDataIsStale: &stale)
                guard outputURL.startAccessingSecurityScopedResource() else {
                    onExit(.cantCreate)
                    return
                }
                defer { outputURL.stopAccessingSecurityScopedResource() }

                var arguments: [String] = [
                    "-m", "davinciauto_core.cli",
                    "--project-id", request.projectId,
                    "--script", request.scriptURL.path,
                    "--output-root", outputURL.path,
                    "--target", request.target,
                    "--provider", request.provider,
                    "--frame-rate", String(request.frameRate),
                    "--concurrency", String(request.concurrency),
                    "--progress-log", logURL.path
                ]
                if request.fakeTTS {
                    arguments.append("--fake-tts")
                }
                if !request.apiKey.isEmpty {
                    arguments += ["--api-key", request.apiKey]
                }

                let proc = Process()
                proc.executableURL = URL(fileURLWithPath: python)
                proc.arguments = arguments
                proc.environment = env
                proc.standardOutput = Pipe()
                let stderrPipe = Pipe()
                proc.standardError = stderrPipe

                try proc.run()
                self.process = proc

                let tailer = JSONLTailer(url: logURL)
                tailer.onEvent = onEvent
                try tailer.start()
                self.tailer = tailer

                proc.waitUntilExit()
                tailer.stop()

                let code = ExitCode(rawValue: proc.terminationStatus) ?? .tempFail
                onExit(code)
            } catch {
                onExit(.unavailable)
            }
        }
    }

    func cancel() {
        process?.terminate()
    }
}
