import AppKit
import Foundation
import SwiftUI
import UniformTypeIdentifiers

@MainActor
final class AppModel: ObservableObject {
    @Published var linkText = ""
    @Published var selectedFormat: OutputFormat = .wav
    @Published private(set) var jobs: [TrackJob] = []
    @Published private(set) var outputFolder: URL

    private let processor: JobProcessor

    init() {
        let defaultFolder = FileManager.default.urls(for: .downloadsDirectory, in: .userDomainMask).first!
            .appendingPathComponent("ForMyDJ", isDirectory: true)
        self.outputFolder = UserDefaults.standard.string(forKey: "outputFolder").map(URL.init(fileURLWithPath:)) ?? defaultFolder
        self.processor = JobProcessor()
        try? FileManager.default.createDirectory(at: outputFolder, withIntermediateDirectories: true)
    }

    func submitLink() {
        let value = linkText.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !value.isEmpty else { return }
        linkText = ""
        enqueue(input: .url(value), format: selectedFormat)
    }

    func handleDrop(providers: [NSItemProvider]) -> Bool {
        for provider in providers {
            _ = provider.loadObject(ofClass: URL.self) { [weak self] url, _ in
                guard let self, let url, url.isFileURL else { return }
                Task { @MainActor in
                    self.enqueue(input: .file(url.path), format: self.selectedFormat)
                }
            }
        }
        return true
    }

    func chooseOutputFolder() {
        let panel = NSOpenPanel()
        panel.canChooseDirectories = true
        panel.canChooseFiles = false
        panel.allowsMultipleSelection = false
        panel.directoryURL = outputFolder

        if panel.runModal() == .OK, let url = panel.url {
            outputFolder = url
            UserDefaults.standard.set(url.path, forKey: "outputFolder")
            try? FileManager.default.createDirectory(at: url, withIntermediateDirectories: true)
        }
    }

    func clearCache() {
        Task {
            try? await processor.clearCache()
        }
    }

    private func enqueue(input: JobInput, format: OutputFormat) {
        let job = TrackJob(input: input, format: format)
        jobs.insert(job, at: 0)

        Task {
            await processor.process(job: job, outputFolder: outputFolder) { [weak self] updatedJob in
                guard let self else { return }
                self.update(job: updatedJob)
            }
        }
    }

    private func update(job: TrackJob) {
        guard let index = jobs.firstIndex(where: { $0.id == job.id }) else { return }
        jobs[index] = job
    }
}
