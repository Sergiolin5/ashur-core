import Cocoa
import FlutterMacOS

class MainFlutterWindow: NSWindow {
  private var companionPanel: NSPanel?

  override func awakeFromNib() {
    let flutterViewController = FlutterViewController()
    let windowFrame = self.frame
    self.contentViewController = flutterViewController
    self.setFrame(windowFrame, display: true)

    RegisterGeneratedPlugins(registry: flutterViewController)

    super.awakeFromNib()
    installCompanionPanel()
  }

  private func installCompanionPanel() {
    let size = NSSize(width: 80, height: 80)
    let panel = NSPanel(
      contentRect: NSRect(origin: .zero, size: size),
      styleMask: [.borderless, .nonactivatingPanel],
      backing: .buffered,
      defer: false
    )
    panel.isFloatingPanel = true
    panel.level = .floating
    panel.collectionBehavior = [.canJoinAllSpaces, .fullScreenAuxiliary, .stationary]
    panel.hidesOnDeactivate = false
    panel.isOpaque = false
    panel.backgroundColor = .clear
    panel.hasShadow = false
    panel.isMovableByWindowBackground = true
    panel.contentView = CompanionPanelView(owner: self, frame: NSRect(origin: .zero, size: size))

    if let visibleFrame = NSScreen.main?.visibleFrame {
      panel.setFrameOrigin(
      NSPoint(x: visibleFrame.maxX - size.width - 24, y: visibleFrame.maxY - size.height - 86)
      )
    }
    panel.orderFrontRegardless()
    companionPanel = panel
  }

  @objc fileprivate func showAshur() {
    NSApp.activate(ignoringOtherApps: true)
    makeKeyAndOrderFront(nil)
  }

  @objc fileprivate func closeCompanion() {
    companionPanel?.orderOut(nil)
    companionPanel = nil
  }
}

private final class CompanionPanelView: NSView {
  init(owner: MainFlutterWindow, frame: NSRect) {
    super.init(frame: frame)

    let orb = NucleoButton(frame: NSRect(x: 5, y: 4, width: 62, height: 62))
    orb.target = owner
    orb.action = #selector(MainFlutterWindow.showAshur)
    orb.toolTip = "Mostrar Ashur"
    orb.setAccessibilityLabel("Mostrar Ashur")
    addSubview(orb)

    let close = NSButton(
      title: "×",
      target: owner,
      action: #selector(MainFlutterWindow.closeCompanion)
    )
    close.isBordered = false
    close.font = .systemFont(ofSize: 14, weight: .regular)
    close.contentTintColor = NSColor(srgbRed: 0.79, green: 0.82, blue: 0.88, alpha: 0.78)
    close.toolTip = "Ocultar núcleo"
    close.setAccessibilityLabel("Ocultar núcleo")
    close.frame = NSRect(x: 54, y: 54, width: 23, height: 23)
    addSubview(close)
  }

  required init?(coder: NSCoder) {
    nil
  }
}

private final class NucleoButton: NSButton {
  override init(frame frameRect: NSRect) {
    super.init(frame: frameRect)
    isBordered = false
    title = ""
    setButtonType(.momentaryChange)
  }

  required init?(coder: NSCoder) {
    nil
  }

  override func draw(_ dirtyRect: NSRect) {
    let center = NSPoint(x: bounds.midX, y: bounds.midY)
    NSColor(srgbRed: 0.025, green: 0.035, blue: 0.055, alpha: 0.96).setFill()
    NSBezierPath(ovalIn: bounds.insetBy(dx: 1, dy: 1)).fill()
    let rim = NSBezierPath(ovalIn: bounds.insetBy(dx: 1, dy: 1))
    rim.lineWidth = 0.8
    NSColor(srgbRed: 0.79, green: 0.82, blue: 0.88, alpha: 0.32).setStroke()
    rim.stroke()

    drawOrbit(
      center: center,
      width: 43,
      height: 19,
      rotation: -28,
      color: NSColor(srgbRed: 0.79, green: 0.82, blue: 0.88, alpha: 0.82)
    )
    drawOrbit(
      center: center,
      width: 36,
      height: 15,
      rotation: 39,
      color: NSColor(srgbRed: 0.36, green: 0.62, blue: 0.78, alpha: 0.9)
    )

    let glow = NSShadow()
    glow.shadowColor = NSColor(srgbRed: 0.24, green: 0.78, blue: 0.9, alpha: 0.62)
    glow.shadowBlurRadius = 9
    glow.set()
    NSColor(srgbRed: 0.24, green: 0.78, blue: 0.9, alpha: 1).setFill()
    NSBezierPath(ovalIn: NSRect(x: center.x - 3.4, y: center.y - 3.4, width: 6.8, height: 6.8)).fill()
    NSShadow().set()
  }

  private func drawOrbit(center: NSPoint, width: CGFloat, height: CGFloat, rotation: CGFloat, color: NSColor) {
    let orbit = NSBezierPath(ovalIn: NSRect(
      x: center.x - width / 2,
      y: center.y - height / 2,
      width: width,
      height: height
    ))
    let transform = NSAffineTransform()
    transform.translateX(by: center.x, yBy: center.y)
    transform.rotate(byDegrees: rotation)
    transform.translateX(by: -center.x, yBy: -center.y)
    orbit.transform(using: transform)
    orbit.lineWidth = 1
    color.setStroke()
    orbit.stroke()
  }
}
