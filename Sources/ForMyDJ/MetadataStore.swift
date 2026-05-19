import Foundation

actor MetadataStore {
    private let fileManager = FileManager.default
    private let encoder = JSONEncoder()
    private let cacheDirectory: URL
    private let activeFile: URL

    init() {
        let appSupport = fileManager.urls(for: .applicationSupportDirectory, in: .userDomainMask).first!
        self.cacheDirectory = appSupport.appendingPathComponent("ForMyDJ", isDirectory: true)
        self.activeFile = cacheDirectory.appendingPathComponent("metadata-active.jsonl")
        encoder.outputFormatting = [.sortedKeys]
    }

    func append(_ report: TrackReport) async throws {
        try fileManager.createDirectory(at: cacheDirectory, withIntermediateDirectories: true)
        let data = try encoder.encode(report)
        let line = data + Data([0x0A])

        if fileManager.fileExists(atPath: activeFile.path) {
            let handle = try FileHandle(forWritingTo: activeFile)
            try handle.seekToEnd()
            try handle.write(contentsOf: line)
            try handle.close()
        } else {
            try line.write(to: activeFile)
        }

        if try lineCount(activeFile) >= 50 {
            try await compressActiveFile()
        }
    }

    func clear() async throws {
        guard fileManager.fileExists(atPath: cacheDirectory.path) else { return }
        try fileManager.removeItem(at: cacheDirectory)
    }

    private func lineCount(_ url: URL) throws -> Int {
        let data = try Data(contentsOf: url)
        return data.reduce(0) { count, byte in byte == 0x0A ? count + 1 : count }
    }

    private func compressActiveFile() async throws {
        let archive = cacheDirectory.appendingPathComponent("metadata-\(Int(Date().timeIntervalSince1970)).jsonl")
        try fileManager.moveItem(at: activeFile, to: archive)
        _ = try await Shell.run("gzip", ["-f", archive.path])
    }
}

