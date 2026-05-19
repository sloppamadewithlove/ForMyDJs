import SwiftUI
import UniformTypeIdentifiers

struct ContentView: View {
    @ObservedObject var model: AppModel
    @State private var isDropTargeted = false

    var body: some View {
        VStack(spacing: 0) {
            header
            Divider()
            controls
            Divider()
            jobList
        }
        .background(Color(nsColor: .windowBackgroundColor))
        .onDrop(of: [.fileURL], isTargeted: $isDropTargeted) { providers in
            model.handleDrop(providers: providers)
        }
    }

    private var header: some View {
        HStack {
            VStack(alignment: .leading, spacing: 3) {
                Text("ForMyDJ")
                    .font(.system(size: 24, weight: .semibold))
                Text("Local DJ audio intake")
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
            }
            Spacer()
            Button("Clear Cache") {
                model.clearCache()
            }
            Button("Choose Folder") {
                model.chooseOutputFolder()
            }
        }
        .padding(18)
    }

    private var controls: some View {
        VStack(spacing: 12) {
            HStack(spacing: 10) {
                TextField("Paste SoundCloud, YouTube, or direct audio link", text: $model.linkText)
                    .textFieldStyle(.roundedBorder)
                    .onSubmit { model.submitLink() }
                Picker("Format", selection: $model.selectedFormat) {
                    ForEach(OutputFormat.allCases) { format in
                        Text(format.rawValue).tag(format)
                    }
                }
                .pickerStyle(.segmented)
                .frame(width: 210)
                Button("Download") {
                    model.submitLink()
                }
                .keyboardShortcut(.return, modifiers: .command)
                .disabled(model.linkText.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)
            }

            HStack {
                Text("Output: \(model.outputFolder.path)")
                    .font(.caption)
                    .foregroundStyle(.secondary)
                    .lineLimit(1)
                    .truncationMode(.middle)
                Spacer()
                Text("3 active jobs, unlimited queue")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }

            dropZone
        }
        .padding(18)
    }

    private var dropZone: some View {
        ZStack {
            RoundedRectangle(cornerRadius: 8)
                .strokeBorder(isDropTargeted ? Color.accentColor : Color.secondary.opacity(0.35), style: StrokeStyle(lineWidth: 1.5, dash: [7, 5]))
                .background(
                    RoundedRectangle(cornerRadius: 8)
                        .fill(isDropTargeted ? Color.accentColor.opacity(0.08) : Color.clear)
                )
            Text("Drag audio files here to convert, rename, analyze, and export")
                .font(.callout)
                .foregroundStyle(.secondary)
        }
        .frame(height: 72)
    }

    private var jobList: some View {
        List(model.jobs) { job in
            JobRow(job: job)
                .padding(.vertical, 5)
        }
        .overlay {
            if model.jobs.isEmpty {
                ContentUnavailableView("No tracks yet", systemImage: "music.note", description: Text("Paste a link or drop an audio file to start."))
            }
        }
    }
}

private struct JobRow: View {
    let job: TrackJob

    var body: some View {
        VStack(alignment: .leading, spacing: 7) {
            HStack(alignment: .firstTextBaseline) {
                Text(job.title ?? job.input.displayValue)
                    .font(.headline)
                    .lineLimit(1)
                Spacer()
                Text(job.status.rawValue)
                    .font(.caption.weight(.medium))
                    .padding(.horizontal, 8)
                    .padding(.vertical, 4)
                    .background(statusColor.opacity(0.14))
                    .foregroundStyle(statusColor)
                    .clipShape(RoundedRectangle(cornerRadius: 6))
            }

            HStack(spacing: 10) {
                Text(job.artist ?? "Unknown artist")
                Text(job.format.rawValue)
                if let estimatedKey = job.estimatedKey {
                    Text("Key: \(estimatedKey)")
                }
                Text(job.progressText)
            }
            .font(.caption)
            .foregroundStyle(.secondary)

            if let outputPath = job.outputPath {
                Text(outputPath)
                    .font(.caption)
                    .foregroundStyle(.secondary)
                    .lineLimit(1)
                    .truncationMode(.middle)
            }

            if !job.warnings.isEmpty {
                Text(job.warnings.joined(separator: "  |  "))
                    .font(.caption)
                    .foregroundStyle(.orange)
                    .lineLimit(2)
            }

            if let errorMessage = job.errorMessage {
                Text(errorMessage)
                    .font(.caption)
                    .foregroundStyle(.red)
                    .lineLimit(2)
            }
        }
    }

    private var statusColor: Color {
        switch job.status {
        case .finished: .green
        case .failed: .red
        case .queued: .secondary
        default: .accentColor
        }
    }
}
