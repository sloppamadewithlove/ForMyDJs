import Foundation

enum Downloader {
    static func download(url: String, workingDirectory: URL) async throws -> PreparedSource {
        let outputTemplate = workingDirectory.appendingPathComponent("source.%(ext)s").path
        _ = try await Shell.run("yt-dlp", [
            "--no-playlist",
            "--ignore-config",
            "-f", "ba/best",
            "--write-info-json",
            "--write-thumbnail",
            "-o", outputTemplate,
            url
        ])

        let contents = try FileManager.default.contentsOfDirectory(at: workingDirectory, includingPropertiesForKeys: nil)
        guard let audioURL = contents.first(where: { candidate in
            let ext = candidate.pathExtension.lowercased()
            return !["json", "jpg", "jpeg", "png", "webp", "part"].contains(ext)
        }) else {
            throw NSError(domain: "ForMyDJ", code: 10, userInfo: [NSLocalizedDescriptionKey: "No downloadable audio file was produced."])
        }

        let infoJSON = contents.first(where: { $0.lastPathComponent.hasSuffix(".info.json") })
        return PreparedSource(audioURL: audioURL, infoJSON: infoJSON)
    }
}

