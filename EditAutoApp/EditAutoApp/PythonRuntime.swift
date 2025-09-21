import Foundation

enum PythonRuntimeError: Error {
    case missingExecutable(String)
}

struct PythonRuntime {
    struct Paths {
        let executable: String
        let frameworkRoot: String
        let sitePackages: String
        let ffmpeg: String
        let ffprobe: String
    }

    static func resolve() throws -> Paths {
        guard
            let resources = Bundle.main.resourcePath,
            let fwRoot = Bundle.main.privateFrameworksPath.map({ $0 + "/Python.framework/Versions/3.11" })
        else {
            throw PythonRuntimeError.missingExecutable("bundle paths")
        }

        let candidates = [
            fwRoot + "/bin/python3",
            fwRoot + "/Resources/Python.app/Contents/MacOS/Python",
            fwRoot + "/bin/python",
        ]

        guard let exe = candidates.first(where: { FileManager.default.isExecutableFile(atPath: $0) }) else {
            throw PythonRuntimeError.missingExecutable("embedded python executable")
        }

        guard
            let ffmpegURL = Bundle.main.url(forResource: "ffmpeg", withExtension: nil, subdirectory: "bin"),
            let ffprobeURL = Bundle.main.url(forResource: "ffprobe", withExtension: nil, subdirectory: "bin")
        else {
            throw PythonRuntimeError.missingExecutable("ffmpeg/ffprobe")
        }

        return Paths(
            executable: exe,
            frameworkRoot: fwRoot,
            sitePackages: resources + "/python/site-packages",
            ffmpeg: ffmpegURL.path,
            ffprobe: ffprobeURL.path
        )
    }

    static func environment(base: [String: String] = ProcessInfo.processInfo.environment) throws -> [String: String] {
        let paths = try resolve()
        var env = base
        let caches = FileManager.default.urls(for: .cachesDirectory, in: .userDomainMask).first!.path
        env["PYTHONHOME"] = paths.frameworkRoot
        env["PYTHONPATH"] = paths.sitePackages
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        env["PYTHONPYCACHEPREFIX"] = caches + "/pyc"
        env["XDG_CACHE_HOME"] = caches
        env["LC_ALL"] = "en_US_POSIX"
        env["DAVA_FFMPEG_PATH"] = paths.ffmpeg
        env["DAVA_FFPROBE_PATH"] = paths.ffprobe
        return env
    }
}
