# Blink! - Design Document

## Overview

Blink! is a cross-platform desktop application that monitors user eye blinking patterns via webcam and triggers visual reminders to maintain healthy eye habits when blinking becomes infrequent.

---

## Features

### MVP Features (v1.0)

1. **Eye Detection & Blink Tracking**
   - Real-time eye detection using MediaPipe Face Mesh
   - Blink event detection (eye aspect ratio threshold)
   - Blink rate monitoring (blinks per minute)

2. **Configurable Time-Based Rules**
   - User can set trigger duration (X minutes of low blinking)
   - Blink frequency threshold (minimum blinks per minute to consider "healthy")
   - Two animation modes: "Blink Screen" (gentle) and "Irritation" (attention-getting)

3. **Overlay Animations**
   - Full-screen gentle flash/blink animation
   - Shake/red pulse irritation animation
   - Configurable animation duration and intensity

4. **System Tray Integration**
   - Run in background when main window closed
   - Tray icon with context menu (Show, Hide, Settings, Quit)
   - Camera active indicator in tray

5. **Settings Management**
   - Cross-platform config storage (user data directory)
   - Persistent configuration save/load
   - Real-time setting updates

6. **Privacy & Security**
   - Explicit camera active indicator
   - Privacy notice in settings
   - No frame storage, no network transmission
   - Clear "Stop Camera" option

---

### Nice-to-Have "Cool" Features (v1.5+)

1. **Smart Break Suggestions**
   - Integrate 20-20-20 rule recommendations
   - Suggest physical exercises (focus change, eye rolls)
   - Cumulative eye strain tracking dashboard

2. **Customizable Visual Themes**
   - User-selectable overlay colors
   - Preset animation styles (Zen, Focus, Urgent)
   - Dark/light UI theme switching

3. **Statistics & Analytics**
   - Daily/weekly blink rate charts
   - Historical eye health scores
   - Export health reports (CSV/JSON)

4. **Work Session Integration**
   - Detect idle/inactive periods
   - Pause monitoring during away time
   - Work session tagging (Deep Work, Regular)

5. **Smart Notifications**
   - Optional desktop notifications before overlay
   - Gradual alert escalation (subtle → moderate → intense)
   - Calendar/work-hours aware scheduling

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Main Process                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │                    PyQt6 UI Layer                           │ │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐   │ │
│  │  │ Main Window  │  │ Settings Dlg │  │  Overlay Window  │   │ │
│  │  │ (Controls)   │  │ (Config)     │  │  (Animations)    │   │ │
│  │  └──────────────┘  └──────────────┘  └──────────────────┘   │ │
│  │                                                              │ │
│  │  ┌──────────────────────────────────────────────────────┐  │ │
│  │  │         QSystemTrayIcon + Menu                        │  │ │
│  │  └──────────────────────────────────────────────────────┘  │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                              │                                    │
│                              │ PyQt Signals/Slots                 │
│                              ▼                                    │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │                   Application Logic                          │ │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐   │ │
│  │  │ Blink Monitor│  │ Alert Engine │  │ Config Manager   │   │ │
│  │  │ (Rules)      │  │ (Triggers)   │  │ (Persistence)    │   │ │
│  │  └──────────────┘  └──────────────┘  └──────────────────┘   │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                              │                                    │
│                              │ Queue/Pipe                         │
│                              ▼                                    │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │                 Worker Thread (QThread)                     │ │
│  │  ┌──────────────────────────────────────────────────────┐  │ │
│  │  │              Camera Capture Thread                   │  │ │
│  │  │  (OpenCV VideoCapture @ controlled FPS)             │  │ │
│  │  └──────────────────────────────────────────────────────┘  │ │
│  │                              │                                │ │
│  │                              │ Frame Queue                    │ │
│  │                              ▼                                │ │
│  │  ┌──────────────────────────────────────────────────────┐  │ │
│  │  │            Vision Processing Thread                   │  │ │
│  │  │  (MediaPipe Face Mesh + Eye Detection)               │  │ │
│  │  └──────────────────────────────────────────────────────┘  │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                       External Dependencies                        │
│  • MediaPipe Face Mesh (eye landmarks)                           │
│  • OpenCV (camera capture)                                        │
│  • PyQt6 (UI, tray, animations)                                  │
│  • platformdirs (cross-platform paths)                           │
└─────────────────────────────────────────────────────────────────┘
```

---

## Threading Model

### Main Thread (UI Thread)
- **Responsibility**: PyQt event loop, UI updates, user interaction
- **Operations**:
  - Main window rendering and controls
  - Settings dialog
  - Overlay animations (QPropertyAnimation)
  - System tray updates
  - Timer-based state checks

### Worker Thread 1: Camera Capture (QThread)
- **Responsibility**: Frame acquisition with FPS throttling
- **Operations**:
  - OpenCV VideoCapture loop
  - FPS control (sleep to maintain target FPS)
  - Frame resolution management
  - Queue management for processing thread
- **Queue**: Thread-safe queue (max 3 frames to avoid backlog)

### Worker Thread 2: Vision Processing (QThread)
- **Responsibility**: Face/eye detection and blink analysis
- **Operations**:
  - MediaPipe Face Mesh initialization
  - Eye landmark extraction
  - Eye Aspect Ratio (EAR) calculation
  - Blink event detection (threshold comparison)
  - Blink rate statistics (sliding window)
- **Output**: Signals with blink events and statistics to main thread

### Thread Communication
- **Camera → Vision**: Frame queue (deque with maxsize)
- **Vision → UI**: PyQt signals (blinkDetected, statsUpdated, errorOccurred)
- **UI → Vision**: Control signals (startCapture, stopCapture, updateConfig)
- **Synchronization**: Lock-free signaling via Qt's signal-slot mechanism

---

## Privacy & Security Checklist

### ✅ Data Privacy
- [ ] No frame storage to disk (ephemeral RAM-only)
- [ ] No screenshot capture capability
- [ ] No recording/encoding of video streams
- [ ] No telemetry, analytics, or crash reporting
- [ ] No network connectivity (except for pip install)

### ✅ User Control
- [ ] Explicit "Start Camera" button (auto-start optional)
- [ ] Visible "Camera Active" indicator (red dot in tray)
- [ ] Easy "Stop Camera" button in UI and tray menu
- [ ] Privacy notice prominently displayed in Settings
- [ ] Clear statement about on-device processing only

### ✅ Transparency
- [ ] Privacy Policy section in Help/About dialog
- [ ] Show camera resolution and FPS in Settings
- [ ] Display blink statistics to user (not hidden)
- [ ] Explain detection logic in documentation

### ✅ System Security
- [ ] No elevated privileges required
- [ ] No external API calls
- [ ] Config stored in user directory (no registry polution)
- [ ] No background services or auto-start by default

### ✅ Code Security
- [ ] Input validation for config values
- [ ] Safe file permissions for config storage
- [ ] Graceful error handling (no crashes exposing frames)
- [ ] Thread-safe operations for shared state

---

## Performance Plan

### FPS Throttling
- **Target FPS**: 15 FPS (sufficient for blink detection, low CPU)
- **Implementation**: `time.sleep()` in camera capture loop
- **Dynamic Adjustment**: Drop to 10 FPS if CPU > 60%
- **Frame Skipping**: Process every Nth frame during high load

### Resolution Management
- **Default**: 640x480 (balanced detection quality/performance)
- **Optional**: 320x240 (ultra-low power mode)
- **Scaling**: Downsample frames before MediaPipe processing
- **ROI**: Process center 60% of frame (face typically centered)

### MediaPipe Optimization
- **Max Faces**: 1 (single user mode)
- **Model Complexity**: 0 (landmark accuracy > speed)
- **Refine Landmarks**: True (needed for eye precision)
- **Static Image Mode**: False (video stream mode)

### Memory Management
- **Frame Queue**: Max 3 frames (drop oldest if full)
- **Reuse Frames**: Recycle numpy arrays where possible
- **Garbage Collection**: Periodic explicit cleanup in worker thread
- **Peak RAM Target**: < 150 MB

### CPU Usage Targets
- **Idle (camera off)**: < 1% CPU
- **Active (running)**: 10-20% CPU on modern hardware
- **Alert (overlay animation)**: < 5% additional CPU
- **Fallback**: Auto-throttle if CPU > 80%

### Startup Time
- **Target**: < 3 seconds to camera-ready
- **MediaPipe Load**: Cache model, lazy initialization
- **UI Load**: PyQt window < 500ms
- **Config Load**: < 100ms

### Latency
- **Capture-to-Process**: < 100ms
- **Detection-to-UI**: < 50ms (signal propagation)
- **Blink Trigger**: Within 1-2 frames of actual blink

---

## Platform-Specific Considerations

### Windows
- Camera: DirectShow backend (OpenCV default)
- Tray: QSystemTrayIcon with native icon
- Config: `%APPDATA%/Blink/`
- DPI awareness: Set on high-DPI displays

### macOS
- Camera: AVFoundation backend
- Tray: Native Mac menu bar integration
- Config: `~/Library/Application Support/Blink/`
- Permissions: Camera access prompt on first use

### Linux
- Camera: V4L2 backend (test multiple devices)
- Tray: XDG tray specification
- Config: `~/.config/blink/`
- Dependencies: libcamera-dev on some distros

---

## Error Handling Strategy

### Camera Errors
- No camera found: Show error dialog, offer retry/disable
- Camera disconnected: Pause monitoring, show tray warning
- Permission denied: Show permission instructions, exit gracefully

### Vision Errors
- MediaPipe init failure: Log error, disable detection mode
- No face detected: Continue, update "no face" status in UI
- Invalid landmarks: Skip frame, maintain statistics

### UI Errors
- Window close exception: Save config, clean up threads
- Animation crash: Disable overlay, show error notification
- Config corruption: Reset to defaults, notify user

### Thread Errors
- Worker thread crash: Auto-restart or disable feature
- Queue deadlock: Clear queue, log warning
- Signal/slot error: Catch all exceptions, log to file

---

## Logging Strategy

### Log Levels
- **DEBUG**: Frame timestamps, landmark coordinates
- **INFO**: Blink events, config changes, startup/shutdown
- **WARNING**: Camera frame drops, detection failures
- **ERROR**: Thread crashes, init failures, permission issues

### Log Storage
- **Location**: User data directory (`logs/` subdir)
- **Rotation**: 10MB per file, max 5 files
- **Retention**: 30 days (user configurable)
- **Format**: `[TIMESTAMP] [LEVEL] [MODULE] Message`

### Sensitive Data
- **Excluded**: Never log raw frames or landmark coordinates
- **Included**: Blink counts, timestamps, error messages only
- **PII**: No user-identifiable data in logs

---

## Future Extensibility

### Plugin Architecture (v2.0)
- Custom alert types (audio, haptic)
- Alternative vision backends (dlib, OpenPose)
- Export integrations (Fitbit, Apple Health)

### Multi-User Support
- Per-user profiles
- Family license management
- Shared dashboard

### Advanced Analytics
- Machine learning strain prediction
- Personalized blink rate baselines
- Historical trend analysis

### Cloud Features (Opt-in Only)
- Cross-device sync (explicit user consent)
- Health data backup (encrypted)
- Research contribution (anonymized, opt-in)
