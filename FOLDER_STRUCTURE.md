# Blink! - Folder Structure

```
blink/
│
├── DESIGN.md                          # This design document
├── README.md                          # Project overview, installation, usage
├── requirements.txt                   # Python dependencies
├── setup.py                           # Optional: PyPI packaging
├── .gitignore                         # Git ignore rules
│
├── blink/                             # Main package
│   ├── __init__.py                    # Package initialization
│   ├── __main__.py                    # Entry point (`python -m blink`)
│   │
│   ├── core/                          # Core business logic
│   │   ├── __init__.py
│   │   ├── blink_monitor.py           # Blink detection logic & rules engine
│   │   ├── alert_engine.py            # Trigger logic for animations
│   │   └── statistics.py              # Blink statistics & history
│   │
│   ├── vision/                        # Computer vision module
│   │   ├── __init__.py
│   │   ├── face_detector.py           # MediaPipe Face Mesh wrapper
│   │   ├── eye_analyzer.py            # Eye landmark extraction & EAR calculation
│   │   └── blink_detector.py          # Blink event detection (threshold logic)
│   │
│   ├── camera/                        # Camera handling
│   │   ├── __init__.py
│   │   ├── capture_thread.py          # QThread for frame acquisition
│   │   ├── frame_queue.py             # Thread-safe frame queue
│   │   └── camera_manager.py          # Camera lifecycle & device management
│   │
│   ├── ui/                            # PyQt6 UI components
│   │   ├── __init__.py
│   │   ├── main_window.py             # Primary application window
│   │   ├── settings_dialog.py         # Settings/configuration UI
│   │   ├── overlay_window.py          # Full-screen overlay for animations
│   │   ├── tray_icon.py               # System tray integration
│   │   ├── status_widget.py           # Camera active/status indicator
│   │   └── resources/                 # UI assets
│   │       ├── icons/                 # Tray icons, status icons
│   │       │   ├── tray_icon.png
│   │       │   ├── tray_icon_active.png
│   │       │   ├── camera_on.svg
│   │       │   └── camera_off.svg
│   │       ├── styles.qss             # Qt stylesheet (optional)
│   │       └── fonts/                 # Custom fonts (optional)
│   │
│   ├── animations/                    # Animation system
│   │   ├── __init__.py
│   │   ├── base_animation.py          # Abstract base class
│   │   ├── blink_animation.py         # Gentle flash/blink overlay
│   │   ├── irritation_animation.py    # Shake/red pulse animation
│   │   └── animation_manager.py       # Orchestrates animations
│   │
│   ├── config/                        # Configuration management
│   │   ├── __init__.py
│   │   ├── settings.py                # Settings dataclass/model
│   │   ├── config_manager.py         # Load/save to disk
│   │   └── defaults.py                # Default configuration values
│   │
│   ├── threading/                     # Thread utilities
│   │   ├── __init__.py
│   │   ├── vision_worker.py           # QThread for vision processing
│   │   └── signal_bus.py              # Centralized signal routing
│   │
│   ├── utils/                         # Helper utilities
│   │   ├── __init__.py
│   │   ├── logger.py                  # Logging configuration
│   │   ├── platform.py                # Platform-specific helpers
│   │   ├── exceptions.py              # Custom exception classes
│   │   └── validators.py              # Input validation functions
│   │
│   └── app.py                         # Application entry point & orchestrator
│
├── tests/                             # Test suite
│   ├── __init__.py
│   ├── conftest.py                    # Pytest fixtures
│   │
│   ├── test_core/
│   │   ├── __init__.py
│   │   ├── test_blink_monitor.py
│   │   ├── test_alert_engine.py
│   │   └── test_statistics.py
│   │
│   ├── test_vision/
│   │   ├── __init__.py
│   │   ├── test_face_detector.py
│   │   ├── test_eye_analyzer.py
│   │   └── test_blink_detector.py
│   │
│   ├── test_camera/
│   │   ├── __init__.py
│   │   ├── test_frame_queue.py
│   │   └── test_camera_manager.py
│   │
│   ├── test_config/
│   │   ├── __init__.py
│   │   ├── test_config_manager.py
│   │   └── test_settings.py
│   │
│   ├── test_utils/
│   │   ├── __init__.py
│   │   ├── test_validators.py
│   │   └── test_platform.py
│   │
│   └── test_integration/
│       ├── __init__.py
│       ├── test_end_to_end.py
│       └── test_thread_safety.py
│
├── docs/                              # Documentation
│   ├── USER_GUIDE.md                  # End-user instructions
│   ├── PRIVACY.md                     # Privacy policy details
│   ├── API.md                         # Internal API docs (optional)
│   └── ARCHITECTURE.md                # Detailed architecture notes
│
├── scripts/                           # Utility scripts
│   ├── install_deps.py                # Dependency installation helper
│   ├── clean_logs.py                  # Log cleanup utility
│   └── test_camera.py                 # Camera testing script
│
└── assets/                            # Development/Build assets
    ├── blink.ico                      # Windows icon
    ├── blink.icns                     # macOS icon
    └── blink.png                      # Generic icon
```

---

## Key Design Decisions

### Module Organization
- **core/**: Business logic, independent of UI and vision
- **vision/**: Encapsulated ML/vision, testable without UI
- **camera/**: Hardware abstraction, mockable for tests
- **ui/**: Pure PyQt6, clean separation from business logic
- **animations/**: Reusable animation components
- **config/**: Centralized settings management
- **utils/**: Shared utilities, no circular dependencies

### Testing Strategy
- **Unit tests**: Each module independently tested
- **Integration tests**: End-to-end workflows
- **Thread safety**: Verify no race conditions
- **Mocking**: Camera and vision components mocked for fast tests

### Asset Management
- **Icons**: SVG preferred for scalability
- **Styles**: QSS for theme customization
- **Fonts**: Optional, system fonts used by default

---

## Platform-Specific Files (Generated at Build Time)

### Windows
- `dist/Blink-1.0.0.exe` (PyInstaller)
- `installer/BlinkSetup.exe` (NSIS)

### macOS
- `dist/Blink.app` (PyInstaller)
- `dmg/Blink-1.0.0.dmg` (DMG packaging)

### Linux
- `dist/blink` (PyInstaller bundle)
- `deb/blink_1.0.0_amd64.deb` (Debian package)
- `rpm/blink-1.0.0-1.x86_64.rpm` (RPM package)
