import SwiftUI

@main
struct ForMyDJApp: App {
    @StateObject private var model = AppModel()

    var body: some Scene {
        WindowGroup {
            ContentView(model: model)
                .frame(minWidth: 860, minHeight: 560)
        }
        .windowStyle(.titleBar)
    }
}
