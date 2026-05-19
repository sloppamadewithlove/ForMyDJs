import Foundation

enum KeyDetector {
    private static let sampleRate = 11_025
    private static let maxSeconds = 300
    private static let noteNames = ["C", "C#", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B"]
    private static let majorProfile = [6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88]
    private static let minorProfile = [6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17]

    static func detectKey(audioURL: URL, workingDirectory: URL) async throws -> String {
        let rawURL = workingDirectory.appendingPathComponent("keydetect.f32")
        _ = try await Shell.run("ffmpeg", [
            "-hide_banner",
            "-loglevel", "error",
            "-y",
            "-i", audioURL.path,
            "-t", "\(maxSeconds)",
            "-ac", "1",
            "-ar", "\(sampleRate)",
            "-f", "f32le",
            rawURL.path
        ])

        let data = try Data(contentsOf: rawURL)
        let sampleCount = data.count / MemoryLayout<Float>.size
        guard sampleCount > 4096 else { throw NSError(domain: "ForMyDJ", code: 30, userInfo: [NSLocalizedDescriptionKey: "Not enough audio to estimate key."]) }

        let chroma = data.withUnsafeBytes { buffer in
            let samples = buffer.bindMemory(to: Float.self)
            return estimateChroma(samples: samples)
        }

        return bestKey(chroma: chroma)
    }

    private static func estimateChroma(samples: UnsafeBufferPointer<Float>) -> [Double] {
        let frameSize = 4096
        let hop = 4096
        var chroma = Array(repeating: 0.0, count: 12)
        var frameStart = 0

        while frameStart + frameSize < samples.count {
            let rms = rootMeanSquare(samples: samples, start: frameStart, count: frameSize)
            if rms > 0.01 {
                for octave in 2...6 {
                    for note in 0..<12 {
                        let midi = octave * 12 + note
                        let frequency = 440.0 * pow(2.0, Double(midi - 69) / 12.0)
                        chroma[note] += goertzelMagnitude(samples: samples, start: frameStart, count: frameSize, frequency: frequency)
                    }
                }
            }
            frameStart += hop
        }

        let maxValue = chroma.max() ?? 1
        guard maxValue > 0 else { return chroma }
        return chroma.map { $0 / maxValue }
    }

    private static func rootMeanSquare(samples: UnsafeBufferPointer<Float>, start: Int, count: Int) -> Double {
        var sum = 0.0
        for index in start..<(start + count) {
            let value = Double(samples[index])
            sum += value * value
        }
        return sqrt(sum / Double(count))
    }

    private static func goertzelMagnitude(samples: UnsafeBufferPointer<Float>, start: Int, count: Int, frequency: Double) -> Double {
        let omega = 2.0 * Double.pi * frequency / Double(sampleRate)
        let coefficient = 2.0 * cos(omega)
        var q0 = 0.0
        var q1 = 0.0
        var q2 = 0.0

        for offset in 0..<count {
            let window = 0.5 - 0.5 * cos(2.0 * Double.pi * Double(offset) / Double(count - 1))
            q0 = coefficient * q1 - q2 + Double(samples[start + offset]) * window
            q2 = q1
            q1 = q0
        }

        return sqrt(q1 * q1 + q2 * q2 - coefficient * q1 * q2)
    }

    private static func bestKey(chroma: [Double]) -> String {
        var bestScore = -Double.infinity
        var bestName = "Unknown"

        for root in 0..<12 {
            let majorScore = correlation(chroma: chroma, profile: rotate(majorProfile, by: root))
            if majorScore > bestScore {
                bestScore = majorScore
                bestName = "\(noteNames[root]) major"
            }

            let minorScore = correlation(chroma: chroma, profile: rotate(minorProfile, by: root))
            if minorScore > bestScore {
                bestScore = minorScore
                bestName = "\(noteNames[root]) minor"
            }
        }

        return bestName
    }

    private static func rotate(_ values: [Double], by offset: Int) -> [Double] {
        values.indices.map { values[($0 - offset + values.count) % values.count] }
    }

    private static func correlation(chroma: [Double], profile: [Double]) -> Double {
        let chromaMean = chroma.reduce(0, +) / Double(chroma.count)
        let profileMean = profile.reduce(0, +) / Double(profile.count)
        var numerator = 0.0
        var chromaPower = 0.0
        var profilePower = 0.0

        for index in chroma.indices {
            let x = chroma[index] - chromaMean
            let y = profile[index] - profileMean
            numerator += x * y
            chromaPower += x * x
            profilePower += y * y
        }

        return numerator / max(sqrt(chromaPower * profilePower), 0.000001)
    }
}

