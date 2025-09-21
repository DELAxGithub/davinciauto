import Foundation

struct SelfCheckResult: Decodable {
    let ok: Bool
    let deps: [String: String]?
    let ffmpeg: String?
    let ffprobe: String?
    let error: String?
}

enum ExitCode: Int32, Error {
    case ok = 0
    case usage = 64
    case unavailable = 69
    case cantCreate = 73
    case tempFail = 75
}

final class SelfCheckService {
    func run(completion: @escaping (Result<SelfCheckResult, ExitCode>) -> Void) {
        DispatchQueue.global(qos: .userInitiated).async {
            do {
                let env = try PythonRuntime.environment()
                let python = try PythonRuntime.resolve().executable
                let result = try runProcess(
                    executable: python,
                    arguments: ["-m", "davinciauto_core.cli", "--self-check"],
                    environment: env
                )
                guard let code = ExitCode(rawValue: result.code) else {
                    completion(.failure(.tempFail))
                    return
                }
                if code != .ok {
                    completion(.failure(code))
                    return
                }
                let data = Data(result.stdout.utf8)
                let info = try JSONDecoder().decode(SelfCheckResult.self, from: data)
                completion(.success(info))
            } catch {
                completion(.failure(.unavailable))
            }
        }
    }
}
