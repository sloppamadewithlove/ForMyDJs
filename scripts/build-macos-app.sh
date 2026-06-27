#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
APP="$ROOT/dist/ForMyDJ.app"
CONTENTS="$APP/Contents"
MACOS="$CONTENTS/MacOS"
RESOURCES="$CONTENTS/Resources"
LAUNCHER_C="$ROOT/dist/launcher.c"
LAUNCHER_M="$ROOT/dist/launcher.m"

rm -rf "$APP"
mkdir -p "$MACOS" "$RESOURCES"
cp -R "$ROOT/app" "$RESOURCES/app"

ICON_SOURCE="$ROOT/assets/app-icon-source.png"
ICON_KEY=""
if [ -f "$ICON_SOURCE" ]; then
  ICONSET="$ROOT/dist/AppIcon.iconset"
  rm -rf "$ICONSET"
  mkdir -p "$ICONSET"
  # Center-crop to a square so we don't stretch the source aspect ratio when
  # generating the standard macOS icon sizes.
  SRC_W=$(sips -g pixelWidth  "$ICON_SOURCE" | awk '/pixelWidth/  {print $2}')
  SRC_H=$(sips -g pixelHeight "$ICON_SOURCE" | awk '/pixelHeight/ {print $2}')
  if [ "$SRC_W" -lt "$SRC_H" ]; then SQUARE="$SRC_W"; else SQUARE="$SRC_H"; fi
  sips -c "$SQUARE" "$SQUARE" "$ICON_SOURCE" --out "$ICONSET/_square.png" >/dev/null
  for spec in "16:16x16" "32:16x16@2x" "32:32x32" "64:32x32@2x" "128:128x128" "256:128x128@2x" "256:256x256" "512:256x256@2x" "512:512x512" "1024:512x512@2x"; do
    size="${spec%%:*}"
    name="${spec#*:}"
    sips -z "$size" "$size" "$ICONSET/_square.png" --out "$ICONSET/icon_${name}.png" >/dev/null
  done
  rm -f "$ICONSET/_square.png"
  iconutil -c icns "$ICONSET" -o "$RESOURCES/AppIcon.icns"
  rm -rf "$ICONSET"
  ICON_KEY=$'  <key>CFBundleIconFile</key>\n  <string>AppIcon</string>'
fi

cat > "$CONTENTS/Info.plist" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>CFBundleName</key>
  <string>ForMyDJs</string>
  <key>CFBundleDisplayName</key>
  <string>ForMyDJs</string>
  <key>CFBundleIdentifier</key>
  <string>com.sloppamadewithlove.formydj</string>
  <key>CFBundleVersion</key>
  <string>0.2.0</string>
  <key>CFBundleShortVersionString</key>
  <string>0.2.0</string>
  <key>CFBundlePackageType</key>
  <string>APPL</string>
  <key>CFBundleExecutable</key>
  <string>ForMyDJ</string>
${ICON_KEY}
  <key>LSMinimumSystemVersion</key>
  <string>12.0</string>
  <key>NSHighResolutionCapable</key>
  <true/>
  <key>NSAppTransportSecurity</key>
  <dict>
    <key>NSAllowsLocalNetworking</key>
    <true/>
  </dict>
</dict>
</plist>
PLIST

cat > "$LAUNCHER_M" <<'M'
#import <Cocoa/Cocoa.h>
#import <WebKit/WebKit.h>

@interface AppDelegate : NSObject <NSApplicationDelegate, WKNavigationDelegate>
@property(nonatomic, strong) NSWindow *window;
@property(nonatomic, strong) WKWebView *webView;
@property(nonatomic, strong) NSTask *serverTask;
@property(nonatomic) NSInteger loadAttempts;
@end

@implementation AppDelegate

- (void)applicationDidFinishLaunching:(NSNotification *)notification {
    [self buildMenu];
    [self startServer];
    [self buildWindow];
    [self loadAppAfterDelay];
}

- (BOOL)applicationShouldTerminateAfterLastWindowClosed:(NSApplication *)sender {
    return YES;
}

- (void)buildMenu {
    NSMenu *mainMenu = [[NSMenu alloc] initWithTitle:@""];
    NSMenuItem *appMenuItem = [[NSMenuItem alloc] initWithTitle:@""
                                                         action:nil
                                                  keyEquivalent:@""];
    NSMenuItem *editMenuItem = [[NSMenuItem alloc] initWithTitle:@""
                                                          action:nil
                                                   keyEquivalent:@""];
    [mainMenu addItem:appMenuItem];
    [mainMenu addItem:editMenuItem];

    NSMenu *appMenu = [[NSMenu alloc] initWithTitle:@"ForMyDJs"];
    [appMenu addItemWithTitle:@"Quit ForMyDJs"
                       action:@selector(terminate:)
                keyEquivalent:@"q"];
    appMenuItem.submenu = appMenu;

    NSMenu *editMenu = [[NSMenu alloc] initWithTitle:@"Edit"];
    [editMenu addItemWithTitle:@"Cut"
                        action:@selector(cut:)
                 keyEquivalent:@"x"];
    [editMenu addItemWithTitle:@"Copy"
                        action:@selector(copy:)
                 keyEquivalent:@"c"];
    [editMenu addItemWithTitle:@"Paste"
                        action:@selector(paste:)
                 keyEquivalent:@"v"];
    [editMenu addItemWithTitle:@"Delete"
                        action:@selector(delete:)
                 keyEquivalent:@""];
    [editMenu addItem:[NSMenuItem separatorItem]];
    [editMenu addItemWithTitle:@"Select All"
                        action:@selector(selectAll:)
                 keyEquivalent:@"a"];
    editMenuItem.submenu = editMenu;

    NSApp.mainMenu = mainMenu;
}

- (void)applicationWillTerminate:(NSNotification *)notification {
    if (self.serverTask && self.serverTask.isRunning) {
        [self.serverTask terminate];
    }
}

- (void)startServer {
    NSString *resourcePath = [[NSBundle mainBundle] resourcePath];
    NSString *appPath = [resourcePath stringByAppendingPathComponent:@"app"];
    NSString *serverPath = [appPath stringByAppendingPathComponent:@"server.py"];

    self.serverTask = [[NSTask alloc] init];
    self.serverTask.executableURL = [NSURL fileURLWithPath:@"/usr/bin/python3"];
    self.serverTask.arguments = @[serverPath];
    self.serverTask.currentDirectoryURL = [NSURL fileURLWithPath:appPath];

    NSMutableDictionary *environment = [[[NSProcessInfo processInfo] environment] mutableCopy];
    environment[@"FORMYDJ_NO_BROWSER"] = @"1";
    environment[@"FORMYDJ_PORT"] = @"8765";
    self.serverTask.environment = environment;

    NSPipe *outputPipe = [NSPipe pipe];
    self.serverTask.standardOutput = outputPipe;
    self.serverTask.standardError = outputPipe;

    NSError *error = nil;
    [self.serverTask launchAndReturnError:&error];
    if (error) {
        [self showError:[NSString stringWithFormat:@"Could not start ForMyDJs engine: %@", error.localizedDescription]];
    }
}

- (void)buildWindow {
    NSRect frame = NSMakeRect(0, 0, 1080, 720);
    self.window = [[NSWindow alloc] initWithContentRect:frame
                                              styleMask:(NSWindowStyleMaskTitled |
                                                         NSWindowStyleMaskClosable |
                                                         NSWindowStyleMaskMiniaturizable |
                                                         NSWindowStyleMaskResizable)
                                                backing:NSBackingStoreBuffered
                                                  defer:NO];
    self.window.title = @"ForMyDJs";
    [self.window center];

    WKWebViewConfiguration *configuration = [[WKWebViewConfiguration alloc] init];
    // No persistent cache: this WebView only ever loads the freshly-bundled
    // localhost UI, so an app update must never be masked by a stale disk cache.
    configuration.websiteDataStore = [WKWebsiteDataStore nonPersistentDataStore];
    self.webView = [[WKWebView alloc] initWithFrame:self.window.contentView.bounds configuration:configuration];
    self.webView.navigationDelegate = self;
    self.webView.autoresizingMask = NSViewWidthSizable | NSViewHeightSizable;
    [self.window.contentView addSubview:self.webView];
    [self.window makeKeyAndOrderFront:nil];
    [NSApp activateIgnoringOtherApps:YES];
}

- (void)loadAppAfterDelay {
    dispatch_after(dispatch_time(DISPATCH_TIME_NOW, (int64_t)(0.8 * NSEC_PER_SEC)), dispatch_get_main_queue(), ^{
        [self loadApp];
    });
}

- (void)loadApp {
    self.loadAttempts += 1;
    NSURL *url = [NSURL URLWithString:@"http://127.0.0.1:8765"];
    NSURLRequest *request = [NSURLRequest requestWithURL:url
                                            cachePolicy:NSURLRequestReloadIgnoringLocalAndRemoteCacheData
                                        timeoutInterval:30.0];
    [self.webView loadRequest:request];
}

- (void)webView:(WKWebView *)webView didFailNavigation:(WKNavigation *)navigation withError:(NSError *)error {
    [self retryLoadIfNeeded];
}

- (void)webView:(WKWebView *)webView didFailProvisionalNavigation:(WKNavigation *)navigation withError:(NSError *)error {
    [self retryLoadIfNeeded];
}

- (void)retryLoadIfNeeded {
    if (self.loadAttempts >= 20) {
        [self showError:@"The ForMyDJs window opened, but the local engine did not respond. Close and reopen ForMyDJs."];
        return;
    }

    dispatch_after(dispatch_time(DISPATCH_TIME_NOW, (int64_t)(0.5 * NSEC_PER_SEC)), dispatch_get_main_queue(), ^{
        [self loadApp];
    });
}

- (void)showError:(NSString *)message {
    NSAlert *alert = [[NSAlert alloc] init];
    alert.messageText = @"ForMyDJs";
    alert.informativeText = message;
    [alert addButtonWithTitle:@"OK"];
    [alert runModal];
}

@end

int main(int argc, const char * argv[]) {
    @autoreleasepool {
        NSApplication *app = [NSApplication sharedApplication];
        AppDelegate *delegate = [[AppDelegate alloc] init];
        app.delegate = delegate;
        [app run];
    }
    return 0;
}

M

/usr/bin/clang -fobjc-arc -mmacosx-version-min=12.0 "$LAUNCHER_M" -framework Cocoa -framework WebKit -o "$MACOS/ForMyDJ"
rm -f "$LAUNCHER_C" "$LAUNCHER_M"

echo "Built $APP"
