// swift-tools-version: 5.10

import PackageDescription

let package = Package(
    name: "ForMyDJ",
    platforms: [
        .macOS(.v14)
    ],
    products: [
        .executable(name: "ForMyDJ", targets: ["ForMyDJ"])
    ],
    targets: [
        .executableTarget(
            name: "ForMyDJ"
        )
    ]
)
