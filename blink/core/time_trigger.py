"""Time-based trigger logic for animations."""

from __future__ import annotations

from collections import deque
from datetime import datetime, timedelta
from typing import Callable, Deque, Optional

from loguru import logger
from PyQt6.QtCore import QObject

from blink.config.settings import Settings, TriggerLogic
from blink.core.aggregated_store import AggregatedStatsStore
from blink.threading.signal_bus import SignalBus


class TimeTriggerEngine(QObject):
    """Evaluates blink statistics and fires animation requests."""

    def __init__(
        self,
        settings: Settings,
        signal_bus: SignalBus,
        stats_store: Optional[AggregatedStatsStore] = None,
        clock: Callable[[], datetime] = datetime.now,
    ):
        super().__init__()
        self.settings = settings
        self._clock = clock
        self._signal_bus = signal_bus
        self._stats_store = stats_store

        self._blink_times: Deque[datetime] = deque(maxlen=3600)  # up to 1 hour of events
        self._last_trigger_time: Optional[datetime] = None
        self._pause_until: Optional[datetime] = None

        # Wire signals
        self._signal_bus.pause_for_duration.connect(self.pause_for_minutes)
        self._signal_bus.pause_until_tomorrow.connect(self.pause_until_tomorrow)
        self._signal_bus.resume_requested.connect(self.resume)
        self._signal_bus.blink_detected.connect(self._record_blink_time)
        self._signal_bus.statistics_updated.connect(self.evaluate_statistics)

    # ----------------- Public API -----------------
    def update_settings(self, settings: Settings) -> None:
        """Update thresholds and options."""
        self.settings = settings
        if self._stats_store:
            self._stats_store.set_enabled(settings.collect_aggregated_stats)
        logger.info("Time trigger engine settings updated")

    def pause_for_minutes(self, minutes: int) -> None:
        """Pause triggering for a number of minutes."""
        end = self._clock() + timedelta(minutes=minutes)
        self._pause_until = end
        logger.info(f"Paused triggers for {minutes} minutes (until {end.isoformat(timespec='minutes')})")

    def pause_until_tomorrow(self) -> None:
        """Pause until start of next day."""
        now = self._clock()
        tomorrow = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        self._pause_until = tomorrow
        logger.info(f"Paused triggers until tomorrow ({tomorrow.isoformat()})")

    def resume(self) -> None:
        """Resume triggering immediately."""
        self._pause_until = None
        logger.info("Triggering resumed")

    @property
    def is_paused(self) -> bool:
        """Check if currently paused."""
        if self._pause_until is None:
            return False
        return self._clock() < self._pause_until

    @property
    def pause_remaining_seconds(self) -> int:
        """Seconds until pause ends."""
        if not self.is_paused or self._pause_until is None:
            return 0
        return int((self._pause_until - self._clock()).total_seconds())

    # ----------------- Event handlers -----------------
    def _record_blink_time(self) -> None:
        """Track blink timestamps and aggregated stats."""
        now = self._clock()
        self._blink_times.append(now)
        if self._stats_store:
            self._stats_store.record_blink(now)

    def evaluate_statistics(self, stats: dict) -> None:
        """Evaluate trigger rules using latest statistics."""
        if self.is_paused:
            return

        if self.settings.is_quiet_hours(self._clock()):
            logger.debug("Within quiet hours; suppressing triggers")
            return

        now = self._clock()
        should_trigger, reason = self._should_trigger(stats, now)
        if not should_trigger:
            return

        if not self._cooldown_elapsed(now):
            return

        self._last_trigger_time = now
        if self._stats_store:
            self._stats_store.record_trigger(now)

        logger.info(f"Triggering animation due to: {reason}")
        self._signal_bus.alert_triggered.emit()
        self._signal_bus.animation_requested.emit(self.settings.alert_mode)

    # ----------------- Logic helpers -----------------
    def _should_trigger(self, stats: dict, now: datetime) -> tuple[bool, str]:
        """Decide if trigger conditions are met."""
        mode = TriggerLogic(self.settings.trigger_logic)

        no_blink_seconds = stats.get("time_since_last_blink_seconds", 0.0)
        low_rate_bpm = stats.get("blinks_per_minute", 0.0)

        no_blink_condition = no_blink_seconds >= self.settings.no_blink_seconds
        low_rate_condition = self._is_low_rate(now)

        if mode == TriggerLogic.NO_BLINK:
            return (no_blink_condition, "no blink gap exceeded" if no_blink_condition else "")
        if mode == TriggerLogic.LOW_RATE:
            return (low_rate_condition, "blink rate below threshold" if low_rate_condition else "")

        # BOTH: prefer immediate no-blink, otherwise low-rate
        if no_blink_condition:
            return True, "no blink gap exceeded (priority)"
        if low_rate_condition:
            return True, "sustained low blink rate"
        return False, ""

    def _is_low_rate(self, now: datetime) -> bool:
        """Check sustained low blink rate against history."""
        duration = timedelta(minutes=self.settings.low_rate_duration_minutes)
        threshold = self.settings.low_rate_threshold

        window_start = now - duration
        blinks_in_window = sum(1 for ts in self._blink_times if ts >= window_start)
        expected = threshold * self.settings.low_rate_duration_minutes
        return blinks_in_window < expected

    def _cooldown_elapsed(self, now: datetime) -> bool:
        """Respect alert interval cooldown."""
        if self._last_trigger_time is None:
            return True
        cooldown_seconds = self.settings.alert_interval_minutes * 60
        elapsed = (now - self._last_trigger_time).total_seconds()
        if elapsed < cooldown_seconds:
            logger.debug(f"Trigger suppressed; cooldown {elapsed:.0f}s/{cooldown_seconds}s")
            return False
        return True
