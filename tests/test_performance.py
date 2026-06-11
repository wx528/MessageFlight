"""Performance benchmarks for PlaneBanner rendering."""
import sys
import time
from unittest.mock import MagicMock, patch

from PyQt6.QtWidgets import QApplication

from message_flight.plane_banner import PlaneBanner


class TestPlaneBannerPerformance:
    """Measure rendering performance to prevent regressions."""

    def test_100_paint_events_under_100ms(self):
        """100 consecutive paint events should complete in < 100ms total."""
        app = QApplication.instance() or QApplication(sys.argv)
        assert app is not None
        banner = PlaneBanner()
        banner.setFixedSize(400, 80)

        # Ensure cache is built before timing
        banner.paintEvent(MagicMock())

        # Simulate 100 paint events (about 1.6s of 60fps animation)
        start = time.perf_counter()
        for _ in range(100):
            banner.paintEvent(MagicMock())
        elapsed = time.perf_counter() - start

        assert elapsed < 0.100, f"100 paint events took {elapsed * 1000:.1f}ms, expected < 100ms"

    def test_plane_offset_update_does_not_redraw_banner(self):
        """Setting plane_offset should only trigger partial update."""
        with patch("PyQt6.QtWidgets.QWidget.__init__"), \
             patch.object(PlaneBanner, "setFixedSize"):
            banner = PlaneBanner()

        update_calls = []
        banner.update = lambda *args: update_calls.append(args)

        banner.set_plane_offset(0.5)

        # Should be called with a rect (dirty rect), not empty (full rect)
        assert len(update_calls) == 1
        assert len(update_calls[0]) > 0, "Expected dirty rect update, got full update"
