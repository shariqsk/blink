# Blink! - Eye Health Monitor
i be forgetting to blink sometimes lol if you are too use this
program I made while I was bored, used a mix of GLM 4.7 and codex max for programming, used chat gpt 5.2 thinking for the prompts and file strcture. Wanted to see how far I could push GLM 4.7, and suprisingly it did pretty good. it set up the the strcture nicely but left some bugs, which codex came in handy. 
**camera is buggy right now, if you are having issues either press refresh on main screen or go to settings select camera press ok and then wait a bit, should work after that
A cross-platform desktop application that monitors your eye blinking patterns and provides gentle visual reminders to maintain healthy eye habits.**

## Features

- **Real-time Blink Monitoring**: Tracks blink rate using your webcam (on-device processing only)
- **Smart Alerts**: Gentle "blink screen" or attention-getting "irritation" animations when blinking is infrequent
- **Configurable Rules**: Set custom time thresholds and blink frequency targets
- **Privacy-First**: No data collection, no network transmission, all processing happens on your device
- **System Tray**: Runs in background with easy access controls
- **Cross-Platform**: Windows, macOS, and Linux support

## Installation

### Prerequisites
- Python 3.10 or higher
- A webcam (optional for initial UI testing)

### Setup

1. **Clone or download the repository**

2. **Create a virtual environment** (recommended)

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

3. **Install dependencies**

```bash
pip install -r requirements.txt
```

4. **Run the application**

```bash
python -m blink
```

Alternatively, after installing the package:

```bash
pip install -e .
blink
```

## Usage

### First Run

When you first launch Blink!, you'll see:
- **Main Window**: Controls for starting/stopping monitoring and viewing status
- **Settings Dialog**: Configure your blink thresholds and alert preferences
- **System Tray**: Click the tray icon to show/hide the window or access quick controls

### Basic Workflow

1. **Configure Settings**: Open Settings (gear icon or tray menu) to set your preferences
   - **Alert Interval**: How long to wait before triggering an alert (1-60 minutes)
   - **Minimum Blinks/Minute**: Target blink rate (5-30 blinks)
   - **Alert Mode**: Choose "Blink Screen" (gentle) or "Irritation" (attention-getting)
   - **Camera Resolution**: Default (640x480) or Eco (320x240)

2. **Start Monitoring**: Click "Start Monitoring" in the main window
   - The camera indicator will turn red when active
   - Blink statistics will update in real-time
   - Alerts will trigger based on your configured rules

3. **Background Mode**: Close the main window to continue monitoring in the tray
   - Click tray icon to show the window again
   - Use tray menu to start/stop monitoring without showing window

4. **Stop Monitoring**: Click "Stop Monitoring" or use tray menu to pause

### Keyboard Shortcuts

- `Ctrl+Q` (or `Cmd+Q` on Mac): Quit application
- `Ctrl+P` (or `Cmd+P` on Mac): Open Settings

## Privacy & Security

Blink! is designed with privacy as a core principle:

- **No Data Collection**: No telemetry, analytics, or crash reporting
- **No Network Transmission**: All processing happens locally on your device
- **No Frame Storage**: Camera frames are processed in memory only, never saved to disk
- **Camera Control**: You always control when the camera is active
- **Open Source**: Code is transparent and auditable

For full details, see the Privacy section in the Settings dialog.

## Troubleshooting

### Camera Not Detected

- Ensure your webcam is connected and not in use by another application
- Try a different USB port
- Check OS camera permissions (especially on macOS and Windows)

### Application Won't Start

- Ensure Python 3.10+ is installed: `python --version`
- Verify all dependencies are installed: `pip install -r requirements.txt`
- Check logs in your user data directory for detailed error messages

### High CPU Usage

- Switch to "Eco" mode (320x240 resolution) in Settings
- Reduce the target FPS if performance is an issue

## Development

### Running Tests

```bash
pytest
```

### Code Quality

```bash
black blink/
ruff check blink/
mypy blink/
```

### Building Executables

```bash
# Windows
PyInstaller --onefile --windowed --name Blink blink/__main__.py

# macOS
PyInstaller --onefile --windowed --name Blink blink/__main__.py

# Linux
PyInstaller --onefile --windowed --name Blink blink/__main__.py
```

## Configuration

Configuration files are stored in OS-appropriate locations:

- **Windows**: `%APPDATA%\Blink\config.json`
- **macOS**: `~/Library/Application Support/Blink/config.json`
- **Linux**: `~/.config/blink/config.json`

Logs are stored in a `logs/` subdirectory of the config folder.

## License

MIT License - See LICENSE file for details

## Roadmap

Future features planned:
- Statistics dashboard with historical trends
- 20-20-20 rule integration
- Custom animation themes
- Multi-user profiles
- Advanced analytics and reporting

## Support

For issues, questions, or contributions, please visit the project repository.
