"""Aggregated, privacy-preserving stats storage."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, date
from pathlib import Path
from typing import Dict, Optional

from loguru import logger


@dataclass
class AggregatedStats:
    """Container for aggregated statistics."""

    daily_counts: Dict[str, int] = field(default_factory=dict)
    last_trigger_time: Optional[str] = None  # ISO timestamp


class AggregatedStatsStore:
    """Stores daily blink counts and last trigger timestamp."""

    def __init__(self, data_dir: Path, enabled: bool = True):
        self.data_dir = data_dir
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.file_path = self.data_dir / "aggregated_stats.json"
        self.enabled = enabled
        self._state = AggregatedStats()
        self._load()

    def _load(self) -> None:
        """Load aggregated stats if present."""
        if not self.file_path.exists():
            return

        try:
            raw = json.loads(self.file_path.read_text(encoding="utf-8"))
            self._state = AggregatedStats(
                daily_counts=raw.get("daily_counts", {}),
                last_trigger_time=raw.get("last_trigger_time"),
            )
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning(f"Failed to load aggregated stats: {exc}")
            self._state = AggregatedStats()

    def _save(self) -> None:
        """Persist current state."""
        if not self.enabled:
            return

        try:
            payload = {
                "daily_counts": self._state.daily_counts,
                "last_trigger_time": self._state.last_trigger_time,
            }
            self.file_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning(f"Failed to save aggregated stats: {exc}")

    def set_enabled(self, enabled: bool) -> None:
        """Enable or disable persistence."""
        self.enabled = enabled
        if not enabled:
            logger.info("Aggregated stats disabled; keeping existing data but not writing new entries.")

    def record_blink(self, ts: Optional[datetime] = None) -> None:
        """Record a blink event."""
        if not self.enabled:
            return
        ts = ts or datetime.now()
        day: date = ts.date()
        key = day.isoformat()
        self._state.daily_counts[key] = self._state.daily_counts.get(key, 0) + 1
        self._save()

    def record_trigger(self, ts: Optional[datetime] = None) -> None:
        """Record a trigger event."""
        if not self.enabled:
            return
        ts = ts or datetime.now()
        self._state.last_trigger_time = ts.isoformat()
        self._save()

    @property
    def state(self) -> AggregatedStats:
        """Return current stats snapshot."""
        return self._state
