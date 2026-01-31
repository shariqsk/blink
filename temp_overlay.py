from PyQt6.QtWidgets import QApplication
from blink.ui.screen_overlay import ScreenOverlay
import sys
print("before app")
app = QApplication(sys.argv)
print("before overlay")
try:
    overlay = ScreenOverlay()
    print("after overlay")
except Exception as exc:
    import traceback; traceback.print_exc()
