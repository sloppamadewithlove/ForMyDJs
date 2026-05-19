import Foundation

actor AsyncSemaphore {
    private var available: Int
    private var waiters: [CheckedContinuation<Void, Never>] = []

    init(value: Int) {
        self.available = value
    }

    func wait() async {
        if available > 0 {
            available -= 1
            return
        }

        await withCheckedContinuation { continuation in
            waiters.append(continuation)
        }
    }

    func signal() {
        if waiters.isEmpty {
            available += 1
        } else {
            let continuation = waiters.removeFirst()
            continuation.resume()
        }
    }
}

actor JobProcessor {
    private let semaphore = AsyncSemaphore(value: 3)
    private let metadataStore = MetadataStore()

    func process(job initialJob: TrackJob, outputFolder: URL, update: @MainActor @escaping (TrackJob) -> Void) async {
        await semaphore.wait()
        defer { Task { await semaphore.signal() } }

        var job = initialJob
        do {
            try FileManager.default.createDirectory(at: outputFolder, withIntermediateDirectories: true)
            let workingDirectory = try makeWorkingDirectory(jobID: job.id)
            defer { try? FileManager.default.removeItem(at: workingDirectory) }

            job.status = .downloading
            job.progressText = "Preparing source"
            await update(job)

            let source = try await prepareSource(for: job.input, in: workingDirectory)

            job.status = .analyzing
            job.progressText = "Reading metadata"
            await update(job)

            var metadata = try await MetadataExtractor.metadata(for: source.audioURL, infoJSON: source.infoJSON, input: job.input)
            let warnings = WarningBuilder.warnings(for: metadata, requestedFormat: job.format)

            let estimatedKey = try? await KeyDetector.detectKey(audioURL: source.audioURL, workingDirectory: workingDirectory)
            job.estimatedKey = estimatedKey
            job.title = metadata.title
            job.artist = metadata.artist
            job.warnings = warnings
            await update(job)

            job.status = .converting
            job.progressText = "Writing \(job.format.rawValue)"
            await update(job)

            let outputURL = try await AudioConverter.convert(
                sourceURL: source.audioURL,
                metadata: metadata,
                outputFolder: outputFolder,
                format: job.format
            )

            metadata.sourceURL = metadata.sourceURL ?? job.input.displayValue
            job.status = .finished
            job.progressText = "Done"
            job.outputPath = outputURL.path
            await metadataStore.append(
                TrackReport(
                    id: job.id,
                    createdAt: job.createdAt,
                    input: job.input,
                    outputPath: outputURL.path,
                    outputFormat: job.format,
                    metadata: metadata,
                    estimatedKey: estimatedKey,
                    warnings: warnings
                )
            )
            await update(job)
        } catch {
            job.status = .failed
            job.progressText = "Failed"
            job.errorMessage = error.localizedDescription
            await update(job)
        }
    }

    func clearCache() async throws {
        try await metadataStore.clear()
    }

    private func makeWorkingDirectory(jobID: UUID) throws -> URL {
        let url = FileManager.default.temporaryDirectory
            .appendingPathComponent("ForMyDJ", isDirectory: true)
            .appendingPathComponent(jobID.uuidString, isDirectory: true)
        try FileManager.default.createDirectory(at: url, withIntermediateDirectories: true)
        return url
    }

    private func prepareSource(for input: JobInput, in workingDirectory: URL) async throws -> PreparedSource {
        switch input {
        case .file(let path):
            return PreparedSource(audioURL: URL(fileURLWithPath: path), infoJSON: nil)
        case .url(let url):
            return try await Downloader.download(url: url, workingDirectory: workingDirectory)
        }
    }
}

struct PreparedSource {
    let audioURL: URL
    let infoJSON: URL?
}

