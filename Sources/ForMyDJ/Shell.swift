import Foundation

struct CommandResult {
    let status: Int32
    let stdout: String
    let stderr: String
}

enum ShellError: LocalizedError {
    case missingTool(String)
    case failed(tool: String, status: Int32, stderr: String)

    var errorDescription: String? {
        switch self {
        case .missingTool(let tool):
            "\(tool) was not found. Install it with Homebrew or add it to /opt/homebrew/bin."
        case .failed(let tool, let status, let stderr):
            "\(tool) failed with code \(status): \(stderr.trimmingCharacters(in: .whitespacesAndNewlines))"
        }
    }
}

enum ToolLocator {
    static func path(for tool: String) throws -> String {
        let candidates = [
            "/opt/homebrew/bin/\(tool)",
            "/usr/local/bin/\(tool)",
            "/usr/bin/\(tool)",
            "/bin/\(tool)"
        ]

        if let match = candidates.first(where: { FileManager.default.isExecutableFile(atPath: $0) }) {
            return match
        }

        throw ShellError.missingTool(tool)
    }
}

enum Shell {
    static func run(_ tool: String, _ arguments: [String]) async throws -> CommandResult {
        let path = try ToolLocator.path(for: tool)
        return try await run(path: path, toolName: tool, arguments: arguments)
    }

    static func run(path: String, toolName: String, arguments: [String]) async throws -> CommandResult {
        try await withCheckedThrowingContinuation { continuation in
            let process = Process()
            process.executableURL = URL(fileURLWithPath: path)
            process.arguments = arguments

            let stdoutPipe = Pipe()
            let stderrPipe = Pipe()
            process.standardOutput = stdoutPipe
            process.standardError = stderrPipe

            process.terminationHandler = { finishedProcess in
                let stdoutData = stdoutPipe.fileHandleForReading.readDataToEndOfFile()
                let stderrData = stderrPipe.fileHandleForReading.readDataToEndOfFile()
                let stdout = String(data: stdoutData, encoding: .utf8) ?? ""
                let stderr = String(data: stderrData, encoding: .utf8) ?? ""
                let result = CommandResult(status: finishedProcess.terminationStatus, stdout: stdout, stderr: stderr)

                if result.status == 0 {
                    continuation.resume(returning: result)
                } else {
                    continuation.resume(throwing: ShellError.failed(tool: toolName, status: result.status, stderr: stderr))
                }
            }

            do {
                try process.run()
            } catch {
                continuation.resume(throwing: error)
            }
        }
    }
}

