import Foundation

enum WarningBuilder {
    static func warnings(for metadata: SourceMetadata, requestedFormat: OutputFormat) -> [String] {
        var warnings: [String] = []

        if let duration = metadata.duration, duration > 20 * 60 {
            warnings.append("Track is over 20 minutes")
        }

        if metadata.isLossy, requestedFormat != .mp3 {
            warnings.append("\(requestedFormat.rawValue) output is converted from a lossy source")
        }

        if let channelLayout = metadata.channelLayout?.lowercased(), channelLayout.contains("mono") {
            warnings.append("Source appears mono")
        }

        if metadata.title == nil || metadata.artist == nil {
            warnings.append("Metadata is incomplete")
        }

        if let bitrate = metadata.sourceBitrate, metadata.isLossy, bitrate < 192_000 {
            warnings.append("Lossy source bitrate appears low")
        }

        return warnings
    }
}

