import Foundation

enum OutputFormat: String, CaseIterable, Codable, Identifiable {
    case wav = "WAV"
    case aiff = "AIFF"
    case mp3 = "MP3"

    var id: String { rawValue }

    var fileExtension: String {
        switch self {
        case .wav: "wav"
        case .aiff: "aiff"
        case .mp3: "mp3"
        }
    }
}

enum JobStatus: String, Codable {
    case queued = "Queued"
    case downloading = "Downloading"
    case analyzing = "Analyzing"
    case converting = "Converting"
    case finished = "Finished"
    case failed = "Failed"
}

enum JobInput: Codable, Equatable {
    case url(String)
    case file(String)

    var displayValue: String {
        switch self {
        case .url(let value): value
        case .file(let value): URL(fileURLWithPath: value).lastPathComponent
        }
    }
}

struct TrackJob: Identifiable, Codable, Equatable {
    let id: UUID
    let input: JobInput
    let format: OutputFormat
    let createdAt: Date
    var status: JobStatus
    var progressText: String
    var outputPath: String?
    var title: String?
    var artist: String?
    var estimatedKey: String?
    var warnings: [String]
    var errorMessage: String?

    init(input: JobInput, format: OutputFormat) {
        self.id = UUID()
        self.input = input
        self.format = format
        self.createdAt = Date()
        self.status = .queued
        self.progressText = "Waiting"
        self.warnings = []
    }
}

struct SourceMetadata: Codable {
    var title: String?
    var artist: String?
    var album: String?
    var genre: String?
    var mood: String?
    var uploader: String?
    var uploadDate: String?
    var sourceURL: String?
    var platform: String?
    var duration: Double?
    var thumbnailURL: String?
    var sourceCodec: String?
    var sourceBitrate: Int?
    var channelLayout: String?
    var sampleRate: Int?
    var isLossy: Bool
}

struct TrackReport: Codable {
    let id: UUID
    let createdAt: Date
    let input: JobInput
    let outputPath: String
    let outputFormat: OutputFormat
    let metadata: SourceMetadata
    let estimatedKey: String?
    let warnings: [String]
}

