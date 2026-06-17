# DockKit Extended Patterns

Deeper examples for DockKit integration covering service architecture,
Vision framework integration, custom animations, multi-camera workflows,
and production patterns.

## Contents

- [Service Architecture](#service-architecture)
- [Vision Framework Integration](#vision-framework-integration)
- [AVCaptureSession Integration](#avcapturesession-integration)
- [Multi-Subject Tracking Logic](#multi-subject-tracking-logic)
- [Custom Motor Animations](#custom-motor-animations)
- [SwiftUI Integration](#swiftui-integration)
- [Camera Control via Accessory Events](#camera-control-via-accessory-events)
- [Error Handling](#error-handling)
- [Testing Patterns](#testing-patterns)

## Service Architecture

Isolate DockKit interactions in a dedicated actor to keep motor control
and tracking off the main thread:

```swift
import DockKit
import AVFoundation
import Spatial

actor DockControlService {
    private var accessory: DockAccessory?
    private var trackingMode: TrackingMode = .system

    enum TrackingMode {
        case system
        case custom
        case manual
    }

    func start() async throws {
        for await stateChange in try DockAccessoryManager.shared.accessoryStateChanges {
            switch stateChange.state {
            case .docked:
                guard let newAccessory = stateChange.accessory else { continue }
                accessory = newAccessory
                try await configureAccessory(newAccessory)
            case .undocked:
                accessory = nil
            @unknown default:
                break
            }
        }
    }

    private func configureAccessory(_ accessory: DockAccessory) async throws {
        try await DockAccessoryManager.shared.setSystemTrackingEnabled(true)
        trackingMode = .system
    }

    func setTrackingMode(_ mode: TrackingMode) async throws {
        trackingMode = mode
        let systemEnabled = mode == .system
        try await DockAccessoryManager.shared.setSystemTrackingEnabled(systemEnabled)
    }

    var isConnected: Bool {
        accessory != nil
    }
}
```

### Separating Camera and Dock Concerns

Follow Apple's sample app pattern: define a `CaptureService` actor for
AVFoundation and a `DockControlService` actor for DockKit. Connect them
through a shared model or delegate protocol:

```swift
protocol CameraCaptureDelegate: AnyObject, Sendable {
    func switchCamera() async
    func startOrStopCapture() async
    func zoom(factor: Double) async
}

extension DockControlService {
    func subscribeToAccessoryEvents(
        _ accessory: DockAccessory,
        cameraDelegate: CameraCaptureDelegate
    ) {
        Task {
            for await event in accessory.accessoryEvents {
                switch event {
                case .cameraShutter:
                    await cameraDelegate.startOrStopCapture()
                case .cameraFlip:
                    await cameraDelegate.switchCamera()
                case .cameraZoom(factor: let factor):
                    await cameraDelegate.zoom(factor: factor)
                case .button(id: _, pressed: _):
                    break
                @unknown default:
                    break
                }
            }
        }
    }
}
```

## Vision Framework Integration

### Hand Tracking

Track a hand pose using Vision and feed observations to DockKit:

```swift
import Vision
import DockKit
import AVFoundation

final class HandTrackingProcessor: NSObject,
    AVCaptureVideoDataOutputSampleBufferDelegate
{
    private let accessory: DockAccessory
    private let captureDevice: AVCaptureDevice

    init(accessory: DockAccessory, captureDevice: AVCaptureDevice) {
        self.accessory = accessory
        self.captureDevice = captureDevice
    }

    func captureOutput(
        _ output: AVCaptureOutput,
        didOutput sampleBuffer: CMSampleBuffer,
        from connection: AVCaptureConnection
    ) {
        guard let pixelBuffer = CMSampleBufferGetImageBuffer(sampleBuffer) else {
            return
        }

        let request = VNDetectHumanHandPoseRequest()
        let handler = VNImageRequestHandler(
            cvPixelBuffer: pixelBuffer,
            options: [:]
        )

        do {
            try handler.perform([request])
            guard let result = request.results?.first else { return }

            // Use the index finger tip as the tracking point
            let thumbTip = try result.recognizedPoint(.thumbTip)
            guard thumbTip.confidence > 0.5 else { return }

            let rect = CGRect(
                x: thumbTip.location.x - 0.05,
                y: thumbTip.location.y - 0.05,
                width: 0.1,
                height: 0.1
            )

            let observation = DockAccessory.Observation(
                identifier: 0,
                type: .object,
                rect: rect,
                faceYawAngle: nil
            )

            let cameraInfo = DockAccessory.CameraInformation(
                captureDevice: captureDevice.deviceType,
                cameraPosition: captureDevice.position,
                orientation: .corrected,
                cameraIntrinsics: nil,
                referenceDimensions: nil
            )

            Task {
                try await accessory.track(
                    [observation],
                    cameraInformation: cameraInfo
                )
            }
        } catch {
            // Handle Vision errors
        }
    }
}
```

### Animal Body Detection

Track pets by detecting animal body poses:

```swift
func detectAnimal(
    in pixelBuffer: CVPixelBuffer,
    accessory: DockAccessory,
    device: AVCaptureDevice
) throws {
    let request = VNDetectAnimalBodyPoseRequest()
    let handler = VNImageRequestHandler(
        cvPixelBuffer: pixelBuffer,
        options: [:]
    )
    try handler.perform([request])

    guard let result = request.results?.first else { return }

    // Use the bounding box from the animal pose
    let allPoints = try result.recognizedPoints(.all)
    let validPoints = allPoints.values.filter { $0.confidence > 0.3 }
    guard !validPoints.isEmpty else { return }

    let xs = validPoints.map(\.location.x)
    let ys = validPoints.map(\.location.y)
    let minX = xs.min()!, maxX = xs.max()!
    let minY = ys.min()!, maxY = ys.max()!

    let rect = CGRect(
        x: minX, y: minY,
        width: maxX - minX, height: maxY - minY
    )

    let observation = DockAccessory.Observation(
        identifier: 1,
        type: .object,
        rect: rect,
        faceYawAngle: nil
    )

    let cameraInfo = DockAccessory.CameraInformation(
        captureDevice: device.deviceType,
        cameraPosition: device.position,
        orientation: .corrected,
        cameraIntrinsics: nil,
        referenceDimensions: nil
    )

    Task {
        try await accessory.track(
            [observation],
            cameraInformation: cameraInfo
        )
    }
}
```

Vision's coordinate system matches DockKit's (normalized, lower-left
origin), so bounding boxes pass through without conversion.

## AVCaptureSession Integration

### Setting Up the Capture Pipeline

```swift
import AVFoundation
import DockKit

actor CaptureService {
    private let session = AVCaptureSession()
    private var currentDevice: AVCaptureDevice?
    private var videoOutput: AVCaptureVideoDataOutput?

    func configure() throws {
        session.beginConfiguration()
        defer { session.commitConfiguration() }

        session.sessionPreset = .high

        guard let camera = AVCaptureDevice.default(
            .builtInWideAngleCamera,
            for: .video,
            position: .front
        ) else {
            throw CaptureError.noCameraAvailable
        }

        let input = try AVCaptureDeviceInput(device: camera)
        guard session.canAddInput(input) else {
            throw CaptureError.cannotAddInput
        }
        session.addInput(input)
        currentDevice = camera

        let output = AVCaptureVideoDataOutput()
        output.alwaysDiscardsLateVideoFrames = true
        guard session.canAddOutput(output) else {
            throw CaptureError.cannotAddOutput
        }
        session.addOutput(output)
        videoOutput = output
    }

    func startRunning() {
        session.startRunning()
    }

    func stopRunning() {
        session.stopRunning()
    }

    enum CaptureError: Error {
        case noCameraAvailable
        case cannotAddInput
        case cannotAddOutput
    }
}
```

### Providing Camera Information from Capture Device

```swift
extension CaptureService {
    func makeCameraInformation() -> DockAccessory.CameraInformation? {
        guard let device = currentDevice else { return nil }
        return DockAccessory.CameraInformation(
            captureDevice: device.deviceType,
            cameraPosition: device.position,
            orientation: .corrected,
            cameraIntrinsics: nil,
            referenceDimensions: nil
        )
    }
}
```

## Multi-Subject Tracking Logic

### Prioritizing by Saliency

```swift
func trackMostSalient(accessory: DockAccessory) async throws {
    for await state in accessory.trackingStates {
        // Find the subject with saliency rank 1 (most important)
        let primary = state.trackedSubjects.first { subject in
            switch subject {
            case .person(let person):
                return person.saliencyRank == 1
            case .object(let object):
                return object.saliencyRank == 1
            }
        }

        if let primary {
            let id: UUID
            switch primary {
            case .person(let person): id = person.identifier
            case .object(let object): id = object.identifier
            }
            try await accessory.selectSubjects([id])
        }
    }
}
```

### Tracking Who Looks at Camera

```swift
func trackEngagedSubjects(accessory: DockAccessory) async throws {
    for await state in accessory.trackingStates {
        let engaged = state.trackedSubjects.compactMap { subject -> UUID? in
            guard case .person(let person) = subject,
                  let confidence = person.lookingAtCameraConfidence,
                  confidence > 0.7 else { return nil }
            return person.identifier
        }
        if !engaged.isEmpty {
            try await accessory.selectSubjects(engaged)
        }
    }
}
```

### Converting Tracking Rects to View Coordinates

Tracked subject rectangles are in normalized coordinates. Convert to
view space for drawing overlays:

```swift
import UIKit

func convertToViewSpace(
    normalizedRect: CGRect,
    viewSize: CGSize
) -> CGRect {
    // DockKit uses lower-left origin; UIKit uses upper-left
    let flippedY = 1.0 - normalizedRect.origin.y - normalizedRect.height
    return CGRect(
        x: normalizedRect.origin.x * viewSize.width,
        y: flippedY * viewSize.height,
        width: normalizedRect.width * viewSize.width,
        height: normalizedRect.height * viewSize.height
    )
}
```

## Custom Motor Animations

### Sweep Animation

Create a horizontal sweep for panoramic capture:

```swift
func performSweep(accessory: DockAccessory) async throws {
    try await DockAccessoryManager.shared.setSystemTrackingEnabled(false)

    // Sweep right
    let rightVelocity = Vector3D(x: 0.0, y: 0.2, z: 0.0)
    try await accessory.setAngularVelocity(rightVelocity)
    try await Task.sleep(for: .seconds(3))

    // Sweep left
    let leftVelocity = Vector3D(x: 0.0, y: -0.2, z: 0.0)
    try await accessory.setAngularVelocity(leftVelocity)
    try await Task.sleep(for: .seconds(6))

    // Sweep back to center
    try await accessory.setAngularVelocity(rightVelocity)
    try await Task.sleep(for: .seconds(3))

    // Stop
    try await accessory.setAngularVelocity(Vector3D())
    try await DockAccessoryManager.shared.setSystemTrackingEnabled(true)
}
```

### Timed Position Sequence

```swift
func lookAround(accessory: DockAccessory) async throws {
    try await DockAccessoryManager.shared.setSystemTrackingEnabled(false)

    let positions: [(yaw: Double, pitch: Double, duration: Double)] = [
        (yaw: -0.5, pitch: 0.0, duration: 1.5),
        (yaw: 0.5, pitch: 0.0, duration: 3.0),
        (yaw: 0.0, pitch: -0.2, duration: 1.5),
        (yaw: 0.0, pitch: 0.0, duration: 1.0),
    ]

    for pos in positions {
        let target = Vector3D(x: pos.pitch, y: pos.yaw, z: 0.0)
        let progress = try accessory.setOrientation(
            target,
            duration: .seconds(pos.duration),
            relative: false
        )
        while !progress.isFinished && !progress.isCancelled {
            try await Task.sleep(for: .milliseconds(100))
        }
    }

    try await DockAccessoryManager.shared.setSystemTrackingEnabled(true)
}
```

## SwiftUI Integration

### Dock Status View

```swift
import SwiftUI
import DockKit

@Observable
final class DockViewModel {
    var isConnected = false
    var accessoryName: String?
    var batteryLevel: Double?
    var isCharging = false
    var trackingMode: TrackingMode = .system

    enum TrackingMode: String, CaseIterable {
        case system = "System"
        case custom = "Custom"
        case manual = "Manual"
    }

    private var accessory: DockAccessory?

    func startObserving() {
        Task {
            do {
                for await stateChange in try DockAccessoryManager.shared.accessoryStateChanges {
                    await MainActor.run {
                        switch stateChange.state {
                        case .docked:
                            isConnected = true
                            accessory = stateChange.accessory
                            accessoryName = stateChange.accessory?.identifier.name
                        case .undocked:
                            isConnected = false
                            accessory = nil
                            accessoryName = nil
                            batteryLevel = nil
                        @unknown default:
                            break
                        }
                    }
                    if let acc = stateChange.accessory, stateChange.state == .docked {
                        observeBattery(acc)
                    }
                }
            } catch {
                // Handle error
            }
        }
    }

    private func observeBattery(_ accessory: DockAccessory) {
        Task {
            do {
                for await battery in try accessory.batteryStates {
                    await MainActor.run {
                        batteryLevel = battery.batteryLevel
                        isCharging = battery.chargeState == .charging
                    }
                }
            } catch {
                // Handle error
            }
        }
    }

    func updateTrackingMode(_ mode: TrackingMode) {
        trackingMode = mode
        Task {
            try await DockAccessoryManager.shared.setSystemTrackingEnabled(
                mode == .system
            )
        }
    }
}
```

```swift
struct DockStatusView: View {
    @State private var viewModel = DockViewModel()

    var body: some View {
        VStack(alignment: .leading) {
            if viewModel.isConnected {
                Label(
                    viewModel.accessoryName ?? "DockKit Accessory",
                    systemImage: "dock.rectangle"
                )
                .font(.headline)

                if let level = viewModel.batteryLevel {
                    HStack {
                        Image(systemName: viewModel.isCharging
                              ? "battery.100percent.bolt"
                              : "battery.75percent")
                        Text("\(Int(level * 100))%")
                    }
                }

                Picker("Tracking", selection: $viewModel.trackingMode) {
                    ForEach(DockViewModel.TrackingMode.allCases, id: \.self) {
                        Text($0.rawValue)
                    }
                }
                .pickerStyle(.segmented)
                .onChange(of: viewModel.trackingMode) { _, newValue in
                    viewModel.updateTrackingMode(newValue)
                }
            } else {
                Label("No Dock Connected", systemImage: "dock.rectangle")
                    .foregroundStyle(.secondary)
            }
        }
        .task {
            viewModel.startObserving()
        }
    }
}
```

### Manual Control Overlay

```swift
struct ManualControlView: View {
    let accessory: DockAccessory
    let speed: Double = 0.2

    var body: some View {
        VStack {
            Button { move(.tiltUp) } label: {
                Image(systemName: "chevron.up")
            }
            HStack {
                Button { move(.panLeft) } label: {
                    Image(systemName: "chevron.left")
                }
                Button { stop() } label: {
                    Image(systemName: "stop.fill")
                }
                Button { move(.panRight) } label: {
                    Image(systemName: "chevron.right")
                }
            }
            Button { move(.tiltDown) } label: {
                Image(systemName: "chevron.down")
            }
        }
        .font(.title)
    }

    enum Direction { case tiltUp, tiltDown, panLeft, panRight }

    private func move(_ direction: Direction) {
        Task {
            var velocity = Vector3D()
            switch direction {
            case .tiltUp:    velocity.x = -speed
            case .tiltDown:  velocity.x = speed
            case .panLeft:   velocity.y = -speed
            case .panRight:  velocity.y = speed
            }
            try await accessory.setAngularVelocity(velocity)
        }
    }

    private func stop() {
        Task {
            try await accessory.setAngularVelocity(Vector3D())
        }
    }
}
```

## Camera Control via Accessory Events

### Implementing Zoom

```swift
func handleZoom(factor: Double, device: AVCaptureDevice) {
    do {
        try device.lockForConfiguration()
        let direction = factor > 0 ? 1.0 : -1.0
        let scale = 0.2
        var newZoom = device.videoZoomFactor + direction * scale
        newZoom = max(
            min(newZoom, device.maxAvailableVideoZoomFactor),
            device.minAvailableVideoZoomFactor
        )
        device.videoZoomFactor = newZoom
        device.unlockForConfiguration()
    } catch {
        // Handle lock error
    }
}
```

### Button-Triggered Panorama

```swift
func handlePanorama(
    accessory: DockAccessory,
    buttonID: Int,
    pressed: Bool
) async throws {
    guard buttonID == 5 else { return }

    if pressed {
        try await DockAccessoryManager.shared.setSystemTrackingEnabled(false)
        let velocity = Vector3D(x: 0.0, y: 0.15, z: 0.0)
        try await accessory.setAngularVelocity(velocity)
    } else {
        try await accessory.setAngularVelocity(Vector3D())
        try await DockAccessoryManager.shared.setSystemTrackingEnabled(true)
    }
}
```

## Error Handling

### DockKitError Cases

| Error | Cause | Recovery |
|---|---|---|
| `.notConnected` | No accessory is docked | Wait for `.docked` state |
| `.notSupported` | Operation not available | Check framework availability |
| `.notSupportedByDevice` | Device lacks DockKit support | Degrade gracefully |
| `.invalidParameter` | Bad input value | Validate before calling |
| `.cameraTCCMissing` | Camera permission not granted | Request camera access |
| `.frameRateTooHigh` | Observations exceed 30 fps | Reduce call frequency |
| `.frameRateTooLow` | Observations below 10 fps | Increase call frequency |
| `.noSubjectFound` | No trackable subject detected | Show user guidance |

### Guarding API Calls

```swift
func safeTrack(
    observations: [DockAccessory.Observation],
    cameraInfo: DockAccessory.CameraInformation,
    accessory: DockAccessory
) async {
    do {
        try await accessory.track(observations, cameraInformation: cameraInfo)
    } catch let error as DockKitError {
        switch error {
        case .notConnected:
            // Accessory disconnected, stop tracking loop
            break
        case .frameRateTooHigh:
            // Throttle observation delivery
            break
        case .frameRateTooLow:
            // Speed up frame processing
            break
        case .noSubjectFound:
            // No subject in observations, continue
            break
        default:
            break
        }
    } catch {
        // Unexpected error
    }
}
```

## Testing Patterns

### Conditional DockKit Integration

DockKit requires physical hardware. Use conditional compilation or
runtime checks to keep the app functional without a dock:

```swift
#if canImport(DockKit)
import DockKit
#endif

final class DockController {
    var isDockKitAvailable: Bool {
        #if canImport(DockKit)
        return true
        #else
        return false
        #endif
    }

    func startTracking() async {
        #if canImport(DockKit)
        do {
            for await stateChange in try DockAccessoryManager.shared.accessoryStateChanges {
                // Handle state changes
            }
        } catch {
            // DockKit not available on this device
        }
        #endif
    }
}
```

### Mock Accessory for UI Development

When building UI without hardware, mock the accessory state:

```swift
@Observable
final class MockDockViewModel {
    var isConnected = true
    var accessoryName: String? = "Mock DockKit Stand"
    var batteryLevel: Double? = 0.75
    var isCharging = false
    var trackingMode = "System"

    // Use in SwiftUI previews
    func simulateDisconnect() {
        isConnected = false
        accessoryName = nil
        batteryLevel = nil
    }
}
```
