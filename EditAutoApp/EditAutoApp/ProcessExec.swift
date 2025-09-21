import Foundation

struct ProcessResult {
    let code: Int32
    let stdout: String
    let stderr: String
}

@discardableResult
func runProcess(executable: String, arguments: [String], environment: [String: String]) throws -> ProcessResult {
    let process = Process()
    process.executableURL = URL(fileURLWithPath: executable)
    process.arguments = arguments
    process.environment = environment

    let stdoutPipe = Pipe()
    let stderrPipe = Pipe()
    process.standardOutput = stdoutPipe
    process.standardError = stderrPipe

    try process.run()
    process.waitUntilExit()

    let stdoutData = stdoutPipe.fileHandleForReading.readDataToEndOfFile()
    let stderrData = stderrPipe.fileHandleForReading.readDataToEndOfFile()

    let stdout = String(decoding: stdoutData, as: UTF8.self)
    let stderr = String(decoding: stderrData, as: UTF8.self)
    return ProcessResult(code: process.terminationStatus, stdout: stdout, stderr: stderr)
}
