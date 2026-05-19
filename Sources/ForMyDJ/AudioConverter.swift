import Foundation

enum AudioConverter {
    static func convert(sourceURL: URL, metadata: SourceMetadata, outputFolder: URL, format: OutputFormat) async throws -> URL {
        let artist = sanitize(metadata.artist ?? metadata.uploader ?? "Unknown Artist")
        let title = sanitize(metadata.title ?? sourceURL.deletingPathExtension().lastPathComponent)
        try FileManager.default.createDirectory(at: outputFolder, withIntermediateDirectories: true)

        let baseName = "\(title) - \(artist)"
        let outputURL = uniqueURL(
            in: outputFolder,
            baseName: baseName,
            extension: format.fileExtension
        )

        var args = [
            "-hide_banner",
            "-loglevel", "error",
            "-y",
            "-i", sourceURL.path,
            "-vn",
            "-map_metadata", "0",
            "-ar", "44100",
            "-ac", "2",
            "-af", "silenceremove=start_periods=1:start_threshold=-90dB:stop_periods=1:stop_threshold=-90dB",
            "-metadata", "title=\(metadata.title ?? title)",
            "-metadata", "artist=\(metadata.artist ?? artist)"
        ]

        switch format {
        case .wav:
            args += ["-sample_fmt", "s16", "-c:a", "pcm_s16le"]
        case .aiff:
            args += ["-sample_fmt", "s16", "-c:a", "pcm_s16be", "-f", "aiff"]
        case .mp3:
            args += ["-c:a", "libmp3lame", "-b:a", "320k"]
        }

        args.append(outputURL.path)
        _ = try await Shell.run("ffmpeg", args)
        return outputURL
    }

    private static func sanitize(_ value: String) -> String {
        let illegal = CharacterSet(charactersIn: "/\\?%*|\"<>:")
        let cleaned = value.components(separatedBy: illegal).joined(separator: "")
            .trimmingCharacters(in: .whitespacesAndNewlines)
        return cleaned.isEmpty ? "Unknown" : cleaned
    }

    private static func uniqueURL(in folder: URL, baseName: String, extension ext: String) -> URL {
        var candidate = folder.appendingPathComponent(sanitize(baseName)).appendingPathExtension(ext)
        var index = 2
        while FileManager.default.fileExists(atPath: candidate.path) {
            candidate = folder.appendingPathComponent("\(sanitize(baseName)) \(index)").appendingPathExtension(ext)
            index += 1
        }
        return candidate
    }
}
