import Foundation

enum MetadataExtractor {
    static func metadata(for audioURL: URL, infoJSON: URL?, input: JobInput) async throws -> SourceMetadata {
        var metadata = SourceMetadata(
            title: titleFromFilename(audioURL),
            artist: nil,
            album: nil,
            genre: nil,
            mood: nil,
            uploader: nil,
            uploadDate: nil,
            sourceURL: nil,
            platform: platform(for: input),
            duration: nil,
            thumbnailURL: nil,
            sourceCodec: nil,
            sourceBitrate: nil,
            channelLayout: nil,
            sampleRate: nil,
            isLossy: false
        )

        if let infoJSON, let data = try? Data(contentsOf: infoJSON),
           let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any] {
            metadata.title = string(json, "title") ?? metadata.title
            metadata.artist = string(json, "artist") ?? string(json, "creator") ?? string(json, "uploader")
            metadata.uploader = string(json, "uploader")
            metadata.album = string(json, "album")
            metadata.genre = string(json, "genre")
            metadata.uploadDate = string(json, "upload_date")
            metadata.sourceURL = string(json, "webpage_url") ?? string(json, "original_url")
            metadata.thumbnailURL = string(json, "thumbnail")
            metadata.duration = double(json, "duration")
            metadata.platform = string(json, "extractor_key") ?? metadata.platform
        } else if case .file(let path) = input {
            let parsed = parseTitleArtist(from: URL(fileURLWithPath: path).deletingPathExtension().lastPathComponent)
            metadata.title = parsed.title
            metadata.artist = parsed.artist
        }

        let probe = try await probe(audioURL)
        metadata.duration = metadata.duration ?? probe.duration
        metadata.sourceCodec = probe.codec
        metadata.sourceBitrate = probe.bitrate
        metadata.channelLayout = probe.channelLayout
        metadata.sampleRate = probe.sampleRate
        metadata.isLossy = ["mp3", "aac", "opus", "vorbis", "m4a"].contains(probe.codec?.lowercased() ?? "")

        if metadata.artist == nil {
            let parsed = parseTitleArtist(from: audioURL.deletingPathExtension().lastPathComponent)
            metadata.title = metadata.title ?? parsed.title
            metadata.artist = parsed.artist
        }

        return metadata
    }

    private static func probe(_ audioURL: URL) async throws -> ProbeResult {
        let result = try await Shell.run("ffprobe", [
            "-v", "error",
            "-print_format", "json",
            "-show_format",
            "-show_streams",
            audioURL.path
        ])

        guard let data = result.stdout.data(using: .utf8),
              let json = try JSONSerialization.jsonObject(with: data) as? [String: Any] else {
            return ProbeResult()
        }

        let streams = json["streams"] as? [[String: Any]] ?? []
        let audio = streams.first { ($0["codec_type"] as? String) == "audio" }
        let format = json["format"] as? [String: Any]

        return ProbeResult(
            duration: double(format, "duration"),
            codec: string(audio, "codec_name"),
            bitrate: int(audio, "bit_rate") ?? int(format, "bit_rate"),
            channelLayout: string(audio, "channel_layout"),
            sampleRate: int(audio, "sample_rate")
        )
    }

    private static func titleFromFilename(_ url: URL) -> String {
        url.deletingPathExtension().lastPathComponent
    }

    private static func platform(for input: JobInput) -> String? {
        guard case .url(let value) = input, let host = URL(string: value)?.host else {
            return "Local"
        }
        return host
    }

    private static func parseTitleArtist(from name: String) -> (title: String, artist: String?) {
        let separators = [" - ", " – ", " — "]
        for separator in separators where name.contains(separator) {
            let parts = name.components(separatedBy: separator)
            if parts.count >= 2 {
                return (parts[0].trimmingCharacters(in: .whitespaces), parts[1].trimmingCharacters(in: .whitespaces))
            }
        }
        return (name, nil)
    }
}

private struct ProbeResult {
    var duration: Double?
    var codec: String?
    var bitrate: Int?
    var channelLayout: String?
    var sampleRate: Int?
}

func string(_ dictionary: [String: Any]?, _ key: String) -> String? {
    dictionary?[key] as? String
}

func double(_ dictionary: [String: Any]?, _ key: String) -> Double? {
    if let value = dictionary?[key] as? Double { return value }
    if let value = dictionary?[key] as? Int { return Double(value) }
    if let value = dictionary?[key] as? String { return Double(value) }
    return nil
}

func int(_ dictionary: [String: Any]?, _ key: String) -> Int? {
    if let value = dictionary?[key] as? Int { return value }
    if let value = dictionary?[key] as? String { return Int(value) }
    return nil
}

