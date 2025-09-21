import Foundation
import Darwin

final class JSONLTailer {
    private let url: URL
    private var fileHandle: FileHandle?
    private var dispatchSource: DispatchSourceFileSystemObject?
    private var descriptor: Int32 = -1
    private var offset: UInt64 = 0

    var onEvent: (([String: Any]) -> Void)?

    init(url: URL) {
        self.url = url
    }

    func start() throws {
        if !FileManager.default.fileExists(atPath: url.path) {
            FileManager.default.createFile(atPath: url.path, contents: nil)
        }
        fileHandle = try FileHandle(forReadingFrom: url)
        descriptor = open(url.path, O_EVTONLY)
        dispatchSource = DispatchSource.makeFileSystemObjectSource(fileDescriptor: descriptor, eventMask: .write, queue: .global(qos: .userInitiated))
        dispatchSource?.setEventHandler { [weak self] in self?.drain() }
        dispatchSource?.setCancelHandler { [weak self] in
            if let fd = self?.descriptor, fd >= 0 {
                close(fd)
            }
        }
        dispatchSource?.resume()
        drain()
    }

    private func drain() {
        guard let handle = fileHandle else { return }
        do {
            let attributes = try FileManager.default.attributesOfItem(atPath: url.path)
            let size = (attributes[.size] as? NSNumber)?.uint64Value ?? 0
            if size > offset {
                try handle.seek(toOffset: offset)
                let data = try handle.read(upToCount: Int(size - offset)) ?? Data()
                offset = size
                if let text = String(data: data, encoding: .utf8) {
                    for line in text.split(separator: "\n") {
                        if let jsonData = line.data(using: .utf8),
                           let object = try? JSONSerialization.jsonObject(with: jsonData) as? [String: Any] {
                            onEvent?(object)
                        }
                    }
                }
            }
        } catch {
            // Ignore I/O errors; tailing will resume on next event.
        }
    }

    func stop() {
        dispatchSource?.cancel()
        dispatchSource = nil
        try? fileHandle?.close()
        fileHandle = nil
    }
}
